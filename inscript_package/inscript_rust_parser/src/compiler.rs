// inscript_rust_parser/src/compiler.rs
// AST-to-bytecode compiler — produces OpCodes for the Rust VM

use std::collections::HashMap;
use std::sync::Arc;

use inscript_vm_engine::{OpCode, Value, FuncDef};
use crate::ast::*;

#[derive(Clone)]
struct Scope {
    locals: HashMap<String, usize>,  // name → register index
    next_reg: usize,
}

impl Scope {
    fn new() -> Self {
        Scope {
            locals: HashMap::new(),
            next_reg: 0,
        }
    }

    fn declare(&mut self, name: &str) -> usize {
        let idx = self.next_reg;
        self.locals.insert(name.to_string(), idx);
        self.next_reg += 1;
        idx
    }

    fn resolve(&self, name: &str) -> Option<usize> {
        self.locals.get(name).copied()
    }
}

pub struct Compiler {
    opcodes: Vec<OpCode>,
    constants: Vec<Value>,
    source_map: Vec<usize>,  // line number for each opcode (0 = unknown)
    current_line: usize,     // current source line being compiled
    scopes: Vec<Scope>,
    /// Stack of break-patch-position-lists, one Vec per nesting level
    loop_breaks: Vec<Vec<usize>>,
    /// Stack of continue-patch-position-lists, one Vec per nesting level
    loop_continues: Vec<Vec<usize>>,
    /// Stack of loop-start addresses (for continue target in while/for)
    loop_starts: Vec<usize>,
    functions: Vec<(String, FuncDef)>, // compiled user functions
    discard_expressions: bool, // if false, expression statements leave value on stack
}

impl Compiler {
    pub fn new() -> Self {
        Compiler {
            opcodes: Vec::new(),
            constants: Vec::new(),
            source_map: Vec::new(),
            current_line: 0,
            scopes: vec![Scope::new()],
            loop_breaks: Vec::new(),
            loop_continues: Vec::new(),
            loop_starts: Vec::new(),
            functions: Vec::new(),
            discard_expressions: true,
        }
    }

    pub fn new_with_discard(discard: bool) -> Self {
        let mut c = Compiler::new();
        c.discard_expressions = discard;
        c
    }

    pub fn compile(program: &Program) -> (Vec<OpCode>, Vec<Value>, Vec<(String, FuncDef)>, Vec<usize>) {
        let mut c = Compiler::new();
        c.compile_program(program);
        c.emit(OpCode::Halt);
        (c.opcodes, c.constants, c.functions, c.source_map)
    }

    // ── Opcode helpers ───────────────────────────────────────────

    fn emit(&mut self, op: OpCode) {
        self.source_map.push(self.current_line);
        self.opcodes.push(op);
    }

    fn emit_jump(&mut self, op: OpCode) -> usize {
        let pos = self.opcodes.len();
        self.source_map.push(self.current_line);
        self.opcodes.push(op);
        pos
    }

    fn patch_jump(&mut self, pos: usize) {
        let target = self.opcodes.len();
        self.opcodes[pos] = match &self.opcodes[pos] {
            OpCode::Jump(_) => OpCode::Jump(target),
            OpCode::JumpIfFalse(_) => OpCode::JumpIfFalse(target),
            OpCode::JumpIfTrue(_) => OpCode::JumpIfTrue(target),
            _ => unreachable!(),
        };
    }

    fn add_constant(&mut self, val: Value) -> usize {
        let idx = self.constants.len();
        self.constants.push(val);
        idx
    }

    fn push_const(&mut self, val: Value) {
        match val {
            Value::Int(n) if n >= i32::MIN as i64 && n <= i32::MAX as i64 => {
                self.emit(OpCode::Push(n as i32));
            }
            _ => {
                let idx = self.add_constant(val);
                self.emit(OpCode::LoadConst(idx));
            }
        }
    }

    fn push_bool(&mut self, b: bool) {
        self.emit(if b { OpCode::Push(1) } else { OpCode::Push(0) });
    }

    // ── Scope helpers ────────────────────────────────────────────

    fn declare_var(&mut self, name: &str) -> usize {
        self.scopes.last_mut().unwrap().declare(name)
    }

    fn resolve_var(&self, name: &str) -> Option<usize> {
        for scope in self.scopes.iter().rev() {
            if let Some(idx) = scope.resolve(name) {
                return Some(idx);
            }
        }
        None
    }

    // ── Program ─────────────────────────────────────────────────

    fn compile_program(&mut self, program: &Program) {
        for stmt in &program.statements {
            self.compile_stmt(stmt);
        }
    }

    // ── Statements ───────────────────────────────────────────────

    fn compile_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::Expression(expr, line) => {
                self.current_line = *line;
                self.compile_expr(expr);
                if self.discard_expressions {
                    self.emit(OpCode::Pop);
                }
            }
            Stmt::VarDecl { name, init, line, .. } => {
                self.current_line = *line;
                if let Some(init_expr) = init {
                    self.compile_expr(init_expr);
                } else {
                    self.push_const(Value::Nil);
                }
                let idx = self.declare_var(name);
                self.emit(OpCode::StoreReg(idx));
            }
            Stmt::Return(expr_opt, line) => {
                self.current_line = *line;
                if let Some(expr) = expr_opt {
                    self.compile_expr(expr);
                } else {
                    self.push_const(Value::Nil);
                }
                self.emit(OpCode::Return);
            }
            Stmt::If { condition, then_body, else_body, line } => {
                self.current_line = *line;
                self.compile_expr(condition);
                let else_jump = self.emit_jump(OpCode::JumpIfFalse(0));
                for s in then_body {
                    self.compile_stmt(s);
                }
                if let Some(else_stmts) = else_body {
                    let end_jump = self.emit_jump(OpCode::Jump(0));
                    self.patch_jump(else_jump);
                    self.scopes.push(Scope::new());
                    for s in else_stmts {
                        self.compile_stmt(s);
                    }
                    self.scopes.pop();
                    self.patch_jump(end_jump);
                } else {
                    self.patch_jump(else_jump);
                }
            }
            Stmt::While { condition, body, line } => {
                self.current_line = *line;
                let loop_start = self.opcodes.len();
                self.compile_expr(condition);
                let exit_jump = self.emit_jump(OpCode::JumpIfFalse(0));
                self.loop_breaks.push(Vec::new());
                self.loop_continues.push(Vec::new());
                self.loop_starts.push(loop_start);
                self.scopes.push(Scope::new());
                for s in body {
                    self.compile_stmt(s);
                }
                self.scopes.pop();
                self.loop_starts.pop();
                let continue_patches = self.loop_continues.pop().unwrap();
                let break_patches = self.loop_breaks.pop().unwrap();
                for patch_pos in continue_patches {
                    self.patch_jump(patch_pos);
                }
                self.emit(OpCode::Jump(loop_start));
                self.patch_jump(exit_jump);
                for patch_pos in break_patches {
                    self.patch_jump(patch_pos);
                }
            }
            Stmt::For { target, iter, body, line } => {
                self.current_line = *line;
                self.compile_expr(iter);
                self.emit(OpCode::IterStart);
                let iter_reg = self.scopes.last_mut().unwrap().declare("");
                self.emit(OpCode::StoreReg(iter_reg));

                let loop_start = self.opcodes.len();

                self.emit(OpCode::LoadReg(iter_reg));
                self.emit(OpCode::IterNext);
                self.emit(OpCode::Swap);
                self.emit(OpCode::StoreReg(iter_reg));

                let nil_idx = self.add_constant(Value::Nil);
                self.emit(OpCode::Duplicate);
                self.emit(OpCode::LoadConst(nil_idx));
                self.emit(OpCode::Equal);
                let exit_jump = self.emit_jump(OpCode::JumpIfTrue(0));

                let var_reg = self.declare_var(target);
                self.emit(OpCode::StoreReg(var_reg));

                self.loop_breaks.push(Vec::new());
                self.loop_continues.push(Vec::new());
                self.loop_starts.push(loop_start);
                self.scopes.push(Scope::new());

                for s in body {
                    self.compile_stmt(s);
                }

                self.scopes.pop();
                self.loop_starts.pop();
                let continue_patches = self.loop_continues.pop().unwrap();
                let break_patches = self.loop_breaks.pop().unwrap();

                for patch_pos in &continue_patches {
                    self.opcodes[*patch_pos] = OpCode::Jump(loop_start);
                }

                self.emit(OpCode::Jump(loop_start));
                self.patch_jump(exit_jump);
                self.emit(OpCode::Pop);

                for patch_pos in break_patches {
                    self.opcodes[patch_pos] = OpCode::Jump(self.opcodes.len());
                }
            }
            Stmt::Switch { expr, cases, line } => {
                self.current_line = *line;
                self.compile_expr(expr);
                let mut jumps = Vec::new();
                for (case_expr, body) in cases {
                    self.emit(OpCode::Duplicate);
                    if let Some(ce) = case_expr {
                        self.compile_expr(ce);
                        self.emit(OpCode::Equal);
                        let case_jump = self.emit_jump(OpCode::JumpIfFalse(0));
                        self.emit(OpCode::Pop);
                        for s in body {
                            self.compile_stmt(s);
                        }
                        let end_jump = self.emit_jump(OpCode::Jump(0));
                        self.patch_jump(case_jump);
                        jumps.push(end_jump);
                    } else {
                        self.emit(OpCode::Pop);
                        for s in body {
                            self.compile_stmt(s);
                        }
                        let end_jump = self.emit_jump(OpCode::Jump(0));
                        jumps.push(end_jump);
                    }
                }
                self.emit(OpCode::Pop);
                for j in jumps {
                    self.patch_jump(j);
                }
            }
            Stmt::Break(line) => {
                self.current_line = *line;
                let pos = self.emit_jump(OpCode::Jump(0));
                if let Some(patches) = self.loop_breaks.last_mut() {
                    patches.push(pos);
                }
            }
            Stmt::Continue(line) => {
                self.current_line = *line;
                let pos = self.emit_jump(OpCode::Jump(0));
                if let Some(patches) = self.loop_continues.last_mut() {
                    patches.push(pos);
                }
            }
            Stmt::FunctionDef { name, params, body, line, .. } => {
                self.current_line = *line;
                let mut sub = Compiler::new_with_discard(false);
                for param in params {
                    sub.declare_var(&param.name);
                }
                for s in body {
                    sub.compile_stmt(s);
                }
                sub.emit(OpCode::Return);
                let func_constants_arc: Vec<Arc<Value>> = sub.constants.into_iter()
                    .map(|v| Arc::new(v))
                    .collect();
                let func_def = FuncDef {
                    opcodes: sub.opcodes,
                    constants: func_constants_arc,
                    param_count: params.len(),
                    source_map: sub.source_map,
                };
                self.functions.push((name.clone(), func_def));
            }
            Stmt::ClassDef { name, extends, body, line } => {
                self.current_line = *line;
                let mut fields = Vec::new();
                let mut methods = Vec::new();
                for s in body {
                    match s {
                        Stmt::VarDecl { name: fname, init: Some(init_expr), .. } => {
                            fields.push((fname.clone(), init_expr.clone()));
                        }
                        Stmt::FunctionDef { name: mname, params, body: mbody, .. } => {
                            methods.push((mname.clone(), params.clone(), mbody.clone()));
                        }
                        _ => {}
                    }
                }
                let mut desc_pairs: Vec<(String, Expr)> = Vec::new();
                desc_pairs.push(("__type__".to_string(), Expr::Literal(Literal::String("class".to_string()))));
                desc_pairs.push(("__name__".to_string(), Expr::Literal(Literal::String(name.clone()))));
                let field_pairs: Vec<(String, Expr)> = fields.iter()
                    .map(|(fn_, fe)| (fn_.clone(), fe.clone()))
                    .collect();
                desc_pairs.push(("__fields__".to_string(), Expr::Object(field_pairs)));
                desc_pairs.push(("__parent__".to_string(), match extends {
                    Some(p) => Expr::Literal(Literal::String(p.clone())),
                    None => Expr::Literal(Literal::Nil),
                }));
                let mut method_pairs: Vec<(String, Expr)> = Vec::new();
                for (mname, params, mbody) in &methods {
                    let full_name = format!("{}.{}", name, mname);
                    let _has_self = params.first().map(|p| p.name.as_str()) == Some("self");
                    let mut sub = Compiler::new_with_discard(false);
                    for param in params {
                        sub.declare_var(&param.name);
                    }
                    for s in mbody {
                        sub.compile_stmt(s);
                    }
                    sub.emit(OpCode::Return);
                    let func_constants_arc: Vec<Arc<Value>> = sub.constants.into_iter()
                        .map(|v| Arc::new(v))
                        .collect();
                    let func_def = FuncDef {
                        opcodes: sub.opcodes,
                        constants: func_constants_arc,
                        param_count: params.len(),
                        source_map: sub.source_map,
                    };
                    self.functions.push((full_name.clone(), func_def));
                    method_pairs.push((mname.clone(), Expr::Literal(Literal::String(full_name))));
                }
                desc_pairs.push(("__methods__".to_string(), Expr::Object(method_pairs)));
                let desc_expr = Expr::Object(desc_pairs);
                self.compile_expr(&desc_expr);
                let idx = self.add_constant(Value::String(name.clone()));
                self.emit(OpCode::StoreGlobal(idx));
            }
            Stmt::Throw(_, line) | Stmt::Try { line, .. } => {
                self.current_line = *line;
            }
        }
    }

    // ── Expressions ──────────────────────────────────────────────

    fn compile_expr(&mut self, expr: &Expr) {
        match expr {
            Expr::Literal(lit) => {
                match lit {
                    Literal::Nil => self.push_const(Value::Nil),
                    Literal::Bool(b) => self.push_bool(*b),
                    Literal::Int(n) => self.push_const(Value::Int(*n)),
                    Literal::Float(f) => self.push_const(Value::Float(*f)),
                    Literal::String(s) => self.push_const(Value::String(s.clone())),
                }
            }
            Expr::Identifier(name) => {
                if let Some(idx) = self.resolve_var(name) {
                    self.emit(OpCode::LoadReg(idx));
                } else {
                    // Look up global by name via constant pool
                    let idx = self.add_constant(Value::String(name.clone()));
                    self.emit(OpCode::LoadGlobal(idx));
                }
            }
            Expr::Binary { left, op, right } => {
                if matches!(op, BinOp::Assign) {
                    // Assignment: evaluate RHS, duplicate, store, leave copy for chaining
                    match left.as_ref() {
                        Expr::Identifier(name) => {
                            self.compile_expr(right);
                            self.emit(OpCode::Duplicate);
                            if let Some(idx) = self.resolve_var(name) {
                                self.emit(OpCode::StoreReg(idx));
                            } else {
                                let idx = self.add_constant(Value::String(name.clone()));
                                self.emit(OpCode::StoreGlobal(idx));
                            }
                        }
                        Expr::Member { object, property } => {
                            self.compile_expr(object);
                            self.push_const(Value::String(property.clone()));
                            self.compile_expr(right);
                            self.emit(OpCode::Duplicate);
                            self.emit(OpCode::SetIndex);
                        }
                        Expr::Index { object, index } => {
                            self.compile_expr(object);
                            self.compile_expr(index);
                            self.compile_expr(right);
                            self.emit(OpCode::Duplicate);
                            self.emit(OpCode::SetIndex);
                        }
                        _ => {
                            self.compile_expr(right);
                            self.emit(OpCode::Pop);
                            self.push_const(Value::Nil);
                        }
                    }
                    return;
                }
                self.compile_expr(left);
                self.compile_expr(right);
                let opcode = match op {
                    BinOp::Add => OpCode::Add,
                    BinOp::Sub => OpCode::Sub,
                    BinOp::Mul => OpCode::Mul,
                    BinOp::Div => OpCode::Div,
                    BinOp::Mod => OpCode::Mod,
                    BinOp::Power => OpCode::Power,
                    BinOp::Eq => OpCode::Equal,
                    BinOp::Neq => OpCode::NotEqual,
                    BinOp::Lt => OpCode::LessThan,
                    BinOp::Lte => OpCode::LessEqual,
                    BinOp::Gt => OpCode::GreaterThan,
                    BinOp::Gte => OpCode::GreaterEqual,
                    BinOp::And => OpCode::And,
                    BinOp::Or => OpCode::Or,
                    BinOp::BitwiseAnd | BinOp::BitwiseOr | BinOp::BitwiseXor
                    | BinOp::LeftShift | BinOp::RightShift => {
                        // Not fully supported — pop both operands, push nil
                        self.emit(OpCode::Pop);
                        self.emit(OpCode::Pop);
                        self.push_const(Value::Nil);
                        return;
                    }
                    BinOp::Assign => unreachable!(), // handled above
                };
                self.emit(opcode);
            }
            Expr::Unary { op, operand } => {
                self.compile_expr(operand);
                match op {
                    UnaryOp::Neg => self.emit(OpCode::Negate),
                    UnaryOp::Not => self.emit(OpCode::Not),
                    UnaryOp::BitwiseNot => {
                        // Not supported — emit nop
                        self.push_const(Value::Nil);
                    }
                }
            }
            Expr::Call { callee, args } => {
                self.compile_expr(callee);
                for arg in args {
                    self.compile_expr(arg);
                }
                self.emit(OpCode::Call(args.len()));
            }
            Expr::Member { object, property } => {
                self.compile_expr(object);
                // Push property name as constant
                self.push_const(Value::String(property.clone()));
                // Use Index to get field
                self.emit(OpCode::Index);
            }
            Expr::Index { object, index } => {
                self.compile_expr(object);
                self.compile_expr(index);
                self.emit(OpCode::Index);
            }
            Expr::Array(items) => {
                for item in items {
                    self.compile_expr(item);
                }
                self.emit(OpCode::CreateArray(items.len()));
            }
            Expr::Object(pairs) => {
                for (key, val) in pairs {
                    self.push_const(Value::String(key.clone()));
                    self.compile_expr(val);
                }
                self.emit(OpCode::CreateObject(pairs.len()));
            }
            Expr::Ternary { condition, then_expr, else_expr } => {
                self.compile_expr(condition);
                let else_jump = self.emit_jump(OpCode::JumpIfFalse(0));
                self.compile_expr(then_expr);
                let end_jump = self.emit_jump(OpCode::Jump(0));
                self.patch_jump(else_jump);
                self.compile_expr(else_expr);
                self.patch_jump(end_jump);
            }
            Expr::Lambda { params, body, .. } => {
                // Compile lambda as an anonymous function
                let mut sub = Compiler::new_with_discard(false);
                for param in params {
                    sub.declare_var(&param.name);
                }
                sub.compile_expr(body);
                sub.emit(OpCode::Return);
                let func_constants_arc: Vec<Arc<Value>> = sub.constants.into_iter()
                    .map(|v| Arc::new(v))
                    .collect();
                let func_def = FuncDef {
                    opcodes: sub.opcodes,
                    constants: func_constants_arc,
                    param_count: params.len(),
                    source_map: sub.source_map,
                };
                let lambda_name = format!("<lambda>{}", self.functions.len());
                self.functions.push((lambda_name.clone(), func_def));
                let idx = self.add_constant(Value::String(lambda_name));
                self.emit(OpCode::LoadGlobal(idx));
            }
            Expr::StringInterpolation(parts) => {
                if parts.is_empty() {
                    self.push_const(Value::String(String::new()));
                    return;
                }
                // Compile each part
                let mut first_expr = true;
                for part in parts {
                    match part {
                        InterpolationPart::String(s) => {
                            self.push_const(Value::String(s.clone()));
                        }
                        InterpolationPart::Expr(expr) => {
                            if !first_expr {
                                // Convert non-string to string by wrapping
                                // (runtime handles string conversion via Concat)
                            }
                            self.compile_expr(expr);
                        }
                    }
                    first_expr = false;
                }
                // Use binary Concat ops to reduce everything to one string
                // Stack: [part1, part2, ..., partN] → [string]
                for _ in 1..parts.len() {
                    self.emit(OpCode::Concat);
                }
            }
            Expr::Await(inner) => {
                // Not yet supported — just compile inner
                self.compile_expr(inner);
            }
            Expr::Yield(inner) => {
                if let Some(e) = inner {
                    self.compile_expr(e);
                } else {
                    self.push_const(Value::Nil);
                }
                // Yield not fully supported — treat as expression
            }
            Expr::Propagate(inner) => {
                // Propagate not supported — just compile inner
                self.compile_expr(inner);
            }
        }
    }
}

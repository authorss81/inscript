// inscript_rust_parser/src/ast.rs
// Abstract Syntax Tree node definitions

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub enum Literal {
    Nil,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
}

#[derive(Debug, Clone, Copy)]
pub enum BinOp {
    Add, Sub, Mul, Div, Mod, Power,
    Eq, Neq, Lt, Lte, Gt, Gte,
    And, Or,
    BitwiseAnd, BitwiseOr, BitwiseXor, BitwiseNot,
    LeftShift, RightShift,
}

#[derive(Debug, Clone, Copy)]
pub enum UnaryOp {
    Neg, Not, BitwiseNot,
}

#[derive(Debug, Clone)]
pub struct TypeHint {
    pub name: String,
    pub generics: Vec<TypeHint>,
    pub nullable: bool,
}

#[derive(Debug, Clone)]
pub struct Param {
    pub name: String,
    pub type_hint: Option<TypeHint>,
    pub default: Option<Box<Expr>>,
}

#[derive(Debug, Clone)]
pub enum Expr {
    Literal(Literal),
    Identifier(String),
    Binary {
        left: Box<Expr>,
        op: BinOp,
        right: Box<Expr>,
    },
    Unary {
        op: UnaryOp,
        operand: Box<Expr>,
    },
    Call {
        callee: Box<Expr>,
        args: Vec<Expr>,
    },
    Index {
        object: Box<Expr>,
        index: Box<Expr>,
    },
    Member {
        object: Box<Expr>,
        property: String,
    },
    Ternary {
        condition: Box<Expr>,
        then_expr: Box<Expr>,
        else_expr: Box<Expr>,
    },
    Array(Vec<Expr>),
    Object(Vec<(String, Expr)>),
    Lambda {
        params: Vec<Param>,
        body: Box<Expr>,
        return_type: Option<TypeHint>,
    },
    StringInterpolation(Vec<InterpolationPart>),
    Await(Box<Expr>),
    Yield(Option<Box<Expr>>),
}

#[derive(Debug, Clone)]
pub enum InterpolationPart {
    String(String),
    Expr(Box<Expr>),
}

#[derive(Debug, Clone)]
pub enum Stmt {
    Expression(Expr),
    VarDecl {
        name: String,
        init: Option<Expr>,
        type_hint: Option<TypeHint>,
        mutable: bool,
    },
    FunctionDef {
        name: String,
        params: Vec<Param>,
        body: Vec<Stmt>,
        return_type: Option<TypeHint>,
        is_async: bool,
    },
    ClassDef {
        name: String,
        extends: Option<String>,
        body: Vec<Stmt>,
    },
    If {
        condition: Expr,
        then_body: Vec<Stmt>,
        else_body: Option<Vec<Stmt>>,
    },
    While {
        condition: Expr,
        body: Vec<Stmt>,
    },
    For {
        target: String,
        iter: Expr,
        body: Vec<Stmt>,
    },
    Switch {
        expr: Expr,
        cases: Vec<(Option<Expr>, Vec<Stmt>)>,
    },
    Return(Option<Expr>),
    Break,
    Continue,
    Throw(Expr),
    Try {
        body: Vec<Stmt>,
        catch_clauses: Vec<(String, Vec<Stmt>)>,
        finally_body: Option<Vec<Stmt>>,
    },
}

#[derive(Debug, Clone)]
pub struct Program {
    pub statements: Vec<Stmt>,
}

impl Program {
    pub fn new() -> Self {
        Program {
            statements: Vec::new(),
        }
    }
}

impl Default for Program {
    fn default() -> Self {
        Self::new()
    }
}

// inscript_rust_parser/src/token.rs
// Token types and token stream

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    // ── Literals ──────────────────────────────────
    Int(i64),
    Float(f64),
    String(String),
    Bool(bool),
    Identifier(String),
    Nil,

    // ── Keywords: Declarations ────────────────────
    Let, Const, Fn, Struct, Enum, Class,

    // ── Keywords: Control Flow ────────────────────
    If, Else, While, For, In,
    Return, Break, Continue,
    Switch, Case, Default,
    Try, Catch, Finally, Throw,
    Yield,

    // ── Keywords: Async ───────────────────────────
    Async, Await,

    // ── Keywords: Logical ─────────────────────────
    And, Or, Not,

    // ── Keywords: Lifecycle (scene system) ────────
    OnStart, OnUpdate, OnDraw, OnExit,
    Node, OnReady, OnNodeUpdate, OnNodeDraw,

    // ── Keywords: Type names ──────────────────────
    IntType, FloatType, BoolType, StringType, VoidType,

    // ── Keywords: Module system ───────────────────
    Import, From, As, Export,

    // ── Keywords: Other ───────────────────────────
    SelfKw, Super, Null,
    Spawn, Select, Then, Abstract,
    Interface, Impl, Pub,
    Is, Div, Defer, Repeat, Until,

    // ── Operators: Arithmetic ─────────────────────
    Plus, Minus, Star, Slash, Percent, Power,
    PlusPlus, SlashSlash,

    // ── Operators: Compound Assign ────────────────
    PlusEq, MinusEq, StarEq, SlashEq, PercentEq, PowerEq,

    // ── Operators: Comparison ─────────────────────
    Eq, Neq, Lt, Lte, Gt, Gte,

    // ── Operators: Bitwise ────────────────────────
    BitwiseAnd, BitwiseOr, BitwiseXor, BitwiseNot,
    LeftShift, RightShift,
    AmpEq, PipeEq, CaretEq, LShiftEq, RShiftEq,

    // ── Operators: Assignment ─────────────────────
    Assign,

    // ── Operators: Other ──────────────────────────
    Arrow,        // ->
    FatArrow,     // =>
    Question,
    QuestionDot,  // ?.
    Nullish,      // ??
    NullishEq,    // ??=
    Pipe,         // |
    PipeGt,       // |>

    // ── Delimiters ────────────────────────────────
    LeftParen, RightParen,
    LeftBrace, RightBrace,
    LeftBracket, RightBracket,
    Comma, Dot, Semicolon, Colon,
    DoubleColon,  // ::
    At,           // @

    // ── Range / Spread ────────────────────────────
    DotDot,    // ..
    DotDotEq,  // ..=
    Ellipsis,  // ...

    // ── String interpolation ──────────────────────
    FString(String),

    // ── Special ───────────────────────────────────
    Eof,
}

#[derive(Debug, Clone)]
pub struct TokenInfo {
    pub token: Token,
    pub line: usize,
    pub column: usize,
}

impl TokenInfo {
    pub fn new(token: Token, line: usize, column: usize) -> Self {
        TokenInfo { token, line, column }
    }
}

pub fn precedence(token: &Token) -> u8 {
    match token {
        Token::Or => 1,
        Token::And => 2,
        Token::Eq | Token::Neq => 3,
        Token::Lt | Token::Lte | Token::Gt | Token::Gte => 4,
        Token::BitwiseOr => 5,
        Token::BitwiseXor => 6,
        Token::BitwiseAnd => 7,
        Token::LeftShift | Token::RightShift => 8,
        Token::Plus | Token::Minus => 9,
        Token::Star | Token::Slash | Token::Percent => 10,
        Token::Power => 11,
        Token::Assign => 1,
        _ => 0,
    }
}

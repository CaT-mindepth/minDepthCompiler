import ply.lex as lex

reserved = {'assert': 'ASSERT',
            'true': 'TRUE',
            'false': 'FALSE',
            'int': 'INT',
            'bit': 'BIT',
            'if': 'IF',
            'else': 'ELSE'}
tokens = [
           'NUMBER',
           'ID',
           'ASSIGN',
           'PLUS',
           'MINUS',
           'MULT',
           'EQ',
           'NEQ',
           'LT',
           'GT',
           'LEQ',
           'GEQ',
           'AND',
           'OR',
           'NOT',
           'LPAREN',
           'RPAREN',
           'LBRACE',
           'RBRACE',
           'LBRACKET',
           'RBRACKET',
           'COMMENT',
         ] + list(reserved.values())

t_PLUS = r'\+'
t_MINUS = r'-'
t_MULT = r'\*'
t_EQ = r'=='
t_ASSIGN = r'='
t_NEQ = r'!='
t_LT = r'<'
t_GT = r'>'
t_LEQ = r'<='
t_GEQ = r'>='
t_AND = r'&&'
t_OR = r'\|\|'
t_NOT = r'!'
t_IF = r'\?'
t_ELSE = r':'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'


def t_NUMBER(t):
  r'[-]?\d+'
  return t


def t_ID(t):
  r'[a-zA-Z_][a-zA-Z_.0-9]*(\[(([a-zA-Z_][a-zA-Z_.0-9]*) | ([0-9]+))\])?'
  t.type = reserved.get(t.value, 'ID')
  return t


def t_newline(t):
  r'\n+'
  t.lexer.lineno += len(t.value)


def t_COMMENT(t):
  r'//.*'
  pass
  # No return value. Token discarded


t_ignore = ' ;,\t'


def t_error(t):
  print("Illegal character '%s'" % t.value[0])
  t.lexer.skip(1)

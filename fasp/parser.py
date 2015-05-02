import ply.lex as lex

tokens = (
    'ID',
    'QUOTED_STRING',
    'NUMBER',
    'RATIONAL',
    'DECIMAL',
    'IF',
    'DOT',
    'POPEN',
    'PCLOSE',
    'COMMA',
    'PLUS',
    'PIPE',
    'TIMES',
    'NAF',
    'ARITH',
)

precedence = (
    ('right', 'PIPE', 'PLUS'),
    ('right', 'COMMA', 'TIMES'),
)

t_ID = r'\w+'
t_QUOTED_STRING = r'"[^"]*"|\'[^\']*\''
t_IF = r':-'
t_DOT = r'\.'
t_PIPE = r'\|'
t_PLUS = r'\+'
t_TIMES = r'\*'
t_POPEN = r'\('
t_PCLOSE = r'\)'
t_COMMA = r','

t_ignore_COMMENT = r'%.*'

def t_ARITH(t):
    r'\[[^\]]*\]'
    t.value = t.value[1:-1]
    return t
    
def t_NAF(t):
    r'~|not'
    return t

def t_NUMBER(t):
    r'\d+'
    return t

def t_RATIONAL(t):
    r'\#\d+/\d+'
    t.value = t.value[1:].split('/')
    t.value = "fraction(%s,%s)" % (t.value[0], t.value[1])
    return t

def t_DECIMAL(t):
    r'\#0(\.\d+)?|\#1'
    t.value = t.value[1:]
    if t.value in ['0', '1']: t.value = "fraction(%s,1)" % (t.value,)
    else: t.value = "decimal(%s)" % (t.value[2:],)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t'

def t_error(t):
    print("Illegal character '%s'" % (t.value[0],))
    t.lexer.skip(1)

lexer = lex.lex()
    


import ply.yacc as yacc

def p_line(p):
    '''line : empty
        | rule'''
    p[0] = p[1]
    
def p_empty(p):
    '''empty :'''
    p[0] = ""

def p_rule(p):
    '''rule : head IF body DOT'''
    p[0] = "rule(%s, %s) :- %s." % (p[1], p[3][0], ", ".join(p[3][1]))

def p_fact(p):
    '''rule : head DOT
        | head IF DOT'''
    p[0] = "rule(%s, 1)." % (p[1],)

def p_constraint(p):
    '''rule : IF body DOT'''
    p[0] = "rule(0, %s) :- %s." % (p[2][0], ", ".join(p[2][1]))

def p_head(p):
    '''head : atom'''
    p[0] = p[1]
    
def p_head_comp(p):
    '''head : gor_head
        | gand_head
        | lor_head
        | land_head'''
    p[0] = "%s)" % (p[1],)

def p_gor_head(p):
    '''gor_head : atom PIPE atom'''
    p[0] = "max(%s, %s" % (p[1], p[3])
    
def p_gor_head_rec(p):
    '''gor_head : gor_head PIPE atom'''
    p[0] = "%s,%s" % (p[1], p[3])
    
def p_gand_head(p):
    '''gand_head : atom COMMA atom'''
    p[0] = "min(%s, %s" % (p[1], p[3])
    
def p_gand_head_rec(p):
    '''gand_head : gand_head COMMA atom'''
    p[0] = "%s,%s" % (p[1], p[3])
    
def p_lor_head(p):
    '''lor_head : atom PLUS atom'''
    p[0] = "or(%s, %s" % (p[1], p[3])
    
def p_lor_head_rec(p):
    '''lor_head : lor_head PLUS atom'''
    p[0] = "%s,%s" % (p[1], p[3])
    
def p_land_head(p):
    '''land_head : atom TIMES atom'''
    p[0] = "and(%s, %s" % (p[1], p[3])
    
def p_land_head_rec(p):
    '''land_head : land_head TIMES atom'''
    p[0] = "%s,%s" % (p[1], p[3])

def p_atom_id(p):
    '''atom : ID
        | ID POPEN terms PCLOSE'''
    if len(p) == 2: p[0] = "atom(%s)" % (p[1],)
    else: p[0] = "atom(%s(%s))" % (p[1], p[3])
    
def p_atom_const(p):
    '''atom : RATIONAL
        | DECIMAL'''
    p[0] = p[1]

def p_terms(p):
    '''terms : term
        | terms COMMA term'''
    if len(p) == 2: p[0] = p[1]
    else: p[0] = "%s,%s" % (p[1], p[3])

def p_term(p):
    '''term : ID
        | NUMBER
        | QUOTED_STRING'''
    p[0] = p[1]

def p_body(p):
    '''body : rbody
        | body TIMES rbody
        | body PLUS rbody
        | body COMMA rbody
        | body PIPE rbody'''
    if len(p) == 2: p[0] = p[1]
    elif p[2] == '*': p[0] = ("and(%s,%s)" % (p[1][0], p[3][0]), p[1][1] + p[3][1])
    elif p[2] == '+': p[0] = ("or(%s,%s)" % (p[1][0], p[3][0]), p[1][1] + p[3][1])
    elif p[2] == '|': p[0] = ("max(%s,%s)" % (p[1][0], p[3][0]), p[1][1] + p[3][1])
    elif p[2] == ',': p[0] = ("min(%s,%s)" % (p[1][0], p[3][0]), p[1][1] + p[3][1])

def p_rbody(p):
    '''rbody : atom
        | NAF rbody
        | POPEN body PCLOSE'''
    if len(p) == 2: p[0] = (p[1], [p[1]]) if p[1].startswith("atom") else (p[1], [])
    elif len(p) == 3: p[0] = ("neg(%s)" % (p[2][0],), [])
    else: p[0] = p[2]

def p_rbody_arith(p):
    '''rbody : ARITH'''
    p[0] = ("1", [p[1]])


def p_error(p):
    print("Syntax error in input!")


parser = yacc.yacc()    

if __name__ == "__main__":
    #lexer.input('#1')
    #print(lexer.token())
    
    while True:
        try:
            s = raw_input('calc > ')
        except EOFError:
            break
        if not s: continue
        result = parser.parse(s)
        print(result)
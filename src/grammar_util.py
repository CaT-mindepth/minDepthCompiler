
domino_stateful_grammars = { 
  "if_else_raw" : "grammars/stateful_domino/if_else_raw.sk",
  "nested_ifs" : "grammars/stateful_domino/nested_ifs.sk",
  "pair" : "grammars/stateful_domino/pair.sk", 
  "pred_raw" : "grammars/stateful_domino/pred_raw.sk", 
  "sub" : "grammars/stateful_domino/sub.sk"
}

domino_stateless_grammar = "grammars/stateless_domino/stateless.sk"

num_statefuls_domino = {
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'pred_raw' : 1,
    'sub' : 1
}

num_stateless_domino = {
    'if_else_raw' : 2,
    'nested_ifs' : 2,
    'pair' : 2,
    'pred_raw' : 2,
    'sub' : 2
}

num_inputs = {
    'if_else_raw' : 3,
    'nested_ifs' : 3,
    'pair' : 4,
    'sub' : 3,
    'pred_raw' : 3,
    'tofino' : 4
}

num_stateful_inputs = {
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'sub' : 1,
    'pred_raw' : 1,
    'tofino' : 2
}

num_outputs = {
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'sub' : 1,
    'pred_raw' : 1,
    'tofino' : 2
}


tofino_stateless_grammar = 'grammars/stateless_tofino.sk'
tofino_stateful_grammar = 'grammars/stateful_tofino.sk'

def resolve_stateless(is_tofino):
    if is_tofino:
        return tofino_stateless_grammar
    else:
        return domino_stateless_grammar

def resolve_stateful(name):
    if name == None:
        return tofino_stateful_grammar 
    else: 
        return domino_stateful_grammars[name]
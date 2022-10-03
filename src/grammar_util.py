
domino_stateful_grammars = { 
  "raw": "grammars/stateful_domino/raw.sk",
  "if_else_raw" : "grammars/stateful_domino/if_else_raw.sk",
  "nested_ifs" : "grammars/stateful_domino/nested_ifs.sk",
  "pair" : "grammars/stateful_domino/pair.sk", 
  "pred_raw" : "grammars/stateful_domino/pred_raw.sk", 
  "sub" : "grammars/stateful_domino/sub.sk"
}

# domino_stateless_grammar = "grammars/stateless_domino/stateless.sk"
domino_stateless_grammar = "grammars/stateless_domino/stateless_new.sk"

num_statefuls_domino = {
    'raw': 1,
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'pred_raw' : 1,
    'sub' : 1
}

num_statefuls = {
    'raw': 1,
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'pred_raw' : 1,
    'sub' : 1,
    'tofino': 2,
}

num_stateless_domino = {
    'raw': 1,
    'if_else_raw' : 2,
    'nested_ifs' : 2,
    'pair' : 2,
    'pred_raw' : 2,
    'sub' : 2
}


num_stateless = {
    'raw': 1,
    'if_else_raw' : 2,
    'nested_ifs' : 2,
    'pair' : 2,
    'pred_raw' : 2,
    'sub' : 2,
    'tofino': 2,
}

num_inputs = {
    'raw': 2,
    'if_else_raw' : 3,
    'nested_ifs' : 3,
    'pair' : 4,
    'sub' : 3,
    'pred_raw' : 3,
    'tofino' : 4
}

num_stateful_inputs = {
    'raw': 1,
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'sub' : 1,
    'pred_raw' : 1,
    'tofino' : 2
}

num_outputs = {
    'raw': 1,
    'if_else_raw' : 1,
    'nested_ifs' : 1,
    'pair' : 2,
    'sub' : 1,
    'pred_raw' : 1,
    'tofino' : 2
}


# tofino_stateless_grammar = 'grammars/stateless_tofino.sk'
# tofino_stateless_grammar = 'grammars/stateless_tofino_new.sk'
# one stateless ALU specifically for siphash
tofino_stateless_grammar = 'grammars/stateless_siphash.sk'
tofino_stateful_grammar = 'grammars/stateful_tofino.sk'

def resolve_stateless(is_tofino):
    if is_tofino:
        return tofino_stateless_grammar
    else:
        return domino_stateless_grammar

def resolve_stateful(name):
    if name == None or name == 'tofino':
        return tofino_stateful_grammar 
    else: 
        return domino_stateful_grammars[name]
import logging
import typing

DIVIDER  = '/'
SUBS_BEG = '{'
SUBS_END = '}'
FUNC_BEG = '('
FUNC_END = ')'

class Substitutor:
    def __init__(self):
        self._funcs = {}
        self.reset()

    def reset(self):
        self._func_stack = []
        self._bank = ''

    def add_handler(self, name:str, func:callable):
        self._funcs[name] = func
        return self

    def do_sub(self, locals:dict, src:str) -> str:
        self.reset()
        self._locals = locals
        itr = enumerate(src)
        trg = self._sub_json_token(itr, 0)
        return trg

    def _sub_json_token(self, itr:enumerate, level:int) -> str:
        trg = ''
        for _,c in itr:
            if c == SUBS_BEG:
                # found a nested reference - so resolve it
                trg += self._sub_json_token(itr, level + 1)
            elif c == SUBS_END:
                assert level > 0, 'Mis-matched bracket'
                assert trg in self._locals, f'Unknown key {trg}'
                # trg contains a JSON path to be resolved, and its
                # value used in place of the identified path
                return self._locals[trg]
            elif c == FUNC_BEG:
                # trg contains the name of a function
                trg = trg.upper()
                assert trg in self._funcs.keys(), f'Unknown function: {trg}'
                self._func_stack.append(trg)
                trg = self._sub_json_token(itr, level + 1)
            elif c == FUNC_END:
                # trg contains parms to the function
                assert len(self._func_stack) > 0, 'Mis-matched parentheses'
                fname = self._func_stack.pop(-1)
                return self._funcs[fname](trg)
            else:
                trg += c
                if c == DIVIDER:
                    # bank trg and start over - but keep the separator
                    self._bank += trg
                    trg = ''
        # if (level) error?
        return self._bank + trg

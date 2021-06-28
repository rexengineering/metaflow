"""
This is a Substitution class that takes a dictionary of key/value pairs, and
looks for substitution markers {} in any provided string, as well as provide
means for evoking user-provided functions.

Special characters:
    { - marks the start of a substitution
    } - marks the end of the substitution. All chars collected from the most
        recent { are expected to contain a key present in the procided 
        dictionary and will assert if not present.
    ( - marks the start of a function call. All chars collected are assumed
        to be the name of the function, and must be present in the dictionary
        of functions provided to the Substitutor, and raises if not present.
    ) - marks the end of a function call. All chars collected form the most
        recent ( are taken as the functions arguments, and passed to the
        function.
    / - term divider. When encountered, all collected chars are "banked" and
        the parsing process restarts.

Example
    input:  "R{recur_count}/PT{hour_cnt}H"
    json:   {"recur_count":"3", "hour_cnt":"1"}
    output: "R3/PT1H"

Substitutions can be nested:
    input:  "R{recur_count_{year}}/PT(hour_cnt)H"
    json:   {"recur_count_2021":"3", "recur_count_2021":"5", "year" : "2021", "hour_cnt": "1" }
    output: "R5/PT1H"

    In this case, the value of "year" (2021) is substituted into the first time to make key value
    "recur_count_2021" which is further resolved to the value "5". If "year" is changed to "2020",
    then "year" becomes "2020", the key is "recur_count_2020" which resolves to value "3".

Functions
    Users provide function handlers to the Substituor using the add_handler() method. The parser
    only looks for function call markers '(' and ')', and when found evokes the handler with the
    "arguments" string (all chars collected between the markers) to the handler as it's single
    argument.

    The following argument specifies a handler called 'ADD', which expects a string contianing
    two arguments, but does not do any substitutions (hence the input JSON is empty):

        subr = Substitutor().add_handler('ADD', _func_add)
        subr.do_sub({}, "ADD(NOW, PT3H)")

    The parser separates this string into two parts:
    1. The function name 'ADD'
    2. The argument(s) string 'NOW, PT3H'

    Note that is it the complete responsibility of the handler to determine if the aruments
    make sense. The handler is expected to return the string value to substitute in the
    source string.
 
        def _func_add(parms:str) -> str:
            # split the parms string into tokens, then interpret the tokens
            args = []
            for arg in parms.split(','):
                if arg == 'NOW':
                    # the current time is desired here
                    val = datetime.now(timezone.utc).timestamp()
                else:
                    # otherwise, ask TimedEventManager to parse the arg for us
                    val = TimedEventManager.parse_spec(arg)[1][0]
                args.append(val)
            assert len(args) == 2, 'ADD takes 2 parameters, {len(args)} provided'
            # we have two args, guaranteed to be Numbers at this point.
            # ADD means what it says
            args[0] += args[1]
            # return the string timestamp in ISO 8601 format.
            return datetime.fromtimestamp(args[0]).strftime(ISO_8601_FORMAT)

Functions can be nested.
    input:  "ADD(SUB(NOW, PT3H),PT1W)"

Function arguments can contain substitutions, nested or otherwise.
    input:  "ADD(NOW, PT{hour_cnt}H)"
    json:   {"hour_cnt":"5"}

"""
import logging
import typing

SEPARATOR = '/'
SUBS_BEG  = '{'
SUBS_END  = '}'
FUNC_BEG  = '('
FUNC_END  = ')'

class Substitutor:
    def __init__(self, separator:str = SEPARATOR):
        self._funcs = {}
        self._separator = separator
        self._has_funcs = False
        self.reset()

    def reset(self):
        self._func_stack = []
        self._bank = ''

    def add_handler(self, name:str, func:callable):
        self._funcs[name] = func
        self._has_funcs   = True
        return self

    def remove_handler(self, name:str):
        if name in self._funcs:
            del self._funcs[name]
        return self

    def clear_handlers(self):
        self._funcs = {}
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
                # found a subs reference - so resolve it
                trg += self._sub_json_token(itr, level + 1)
            elif c == SUBS_END:
                assert level > 0, 'Mis-matched bracket'
                assert trg in self._locals, f'Unknown key {trg}'
                # trg contains a JSON path to be resolved, and its
                # value used in place of the identified path
                return self._locals[trg]
            elif self._has_funcs and c == FUNC_BEG:
                # trg contains the name of a function
                trg = trg.upper()
                assert trg in self._funcs.keys(), f'Unknown function: {trg}'
                self._func_stack.append(trg)
                trg = self._sub_json_token(itr, level + 1)
            elif self._has_funcs and c == FUNC_END:
                # trg contains parms to the function
                assert len(self._func_stack) > 0, 'Mis-matched parentheses'
                fname = self._func_stack.pop(-1)
                return self._funcs[fname](trg)
            else:
                trg += c
                if c == self._separator:
                    # bank trg and start over - but keep the separator
                    self._bank += trg
                    trg = ''
        assert level == 0, 'Unexpected EOF on input'
        return self._bank + trg

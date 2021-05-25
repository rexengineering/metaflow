import ast
import logging
import numbers
import re
from enum import Enum
from typing import Any, Dict
from .graphql_wrappers import TYPE, CONSTRAINT

class ValidatorType(Enum):
    BOOLEAN = 'BOOLEAN'
    REQUIRED = 'REQUIRED'
    PERCENTAGE = 'PERCENTAGE'
    POSITIVE = 'POSITIVE'
    RANGE = 'RANGE'
    REGEX = 'REGEX'

class ValidatorRule:
    def __init__(self, type:ValidatorType):
        self.type = type       

class BaseValidator:
    def __init__(self, type:ValidatorType, constraint:Any):
        self.rules = []
        self.type = type
        self.constraint = constraint
        self.msg = None

    def add_rule(self, rule):
        self.rules.append(rule)

    def validate(self, data:Any, locals:Dict[str,any] = None) -> bool:
        raise NotImplementedError('validator missing validate() method')

    def message(self) -> str:
        return self.msg

    def set_message(self, msg:str):
        self.msg = msg

    def as_validator(self) -> dict:
        return {TYPE: self.type, CONSTRAINT: self.constraint}


class RequiredValidator(BaseValidator):
    def __init__(self, constraint:str = None):
        super().__init__(ValidatorType.REQUIRED, constraint)

    def validate(self, data:str, locals:Dict[str,any] = None) -> bool:
        '''
        REQUIRED validator only requires that the data is not empty
        '''
        if self.constraint is not None:
            # evaluate the constraint. since this is python, we'll just eval() the
            # constraint as an expression
            res = eval(self.constraint, {}, locals)
            if not res:
                # if constraint fails then field is not required
                return True  

        wrk = data.strip()
        if len(wrk) == 0:
            self.set_message('Field cannot be empty')
        return len(wrk) > 0


class PositiveValidator(BaseValidator):
    def __init__(self):
        super().__init__(ValidatorType.POSITIVE, None)

    def validate(self, data:any, locals:Dict[str,any] = None) -> bool:
        '''
        POSITIVE means greater than zero for whatever type data is
        '''
        wrk = data
        if isinstance(data,str):
            try:
                wrk = ast.literal_eval(data)
            except ValueError:
                pass

        if isinstance(wrk, numbers.Number):
            if wrk > 0:
                return True
            self.set_message(f'{data} is not positive')
        else:
            self.set_message(f'{data} is not a number')
        return False

class RangeValidator(BaseValidator):
    def __init__(self, constraint:tuple):
        super().__init__(ValidatorType.RANGE, constraint)
        if not isinstance(constraint,tuple) or len(constraint) != 2:
            raise ValueError('Range constraint must be tuple(lower,upper)')
        if constraint[0] > constraint[1]:
            raise ValueError('Lower range can not be greater then upper range')

    def validate(self, data:float, locals:Dict[str,any] = None) -> bool:
        # this might need to get more sophisticated. Do we need
        # specializations for integers, floats, and currency or
        # do we just infer from the data types?
        wrk = data
        if isinstance(data,str):
            try:
                wrk = ast.literal_eval(data)
            except ValueError:
                pass

        if isinstance(wrk, numbers.Number):
            return self.constraint[0] <= wrk and wrk <= self.constraint[1]

        return False

class RegexValidator(BaseValidator):
    def __init__(self, constraint:str):
        super().__init__(ValidatorType.REGEX, constraint)
        try:
            self.pattern = re.compile(constraint)
        except Exception as ex:
            self.set_message(f'Compile of regular expression failed {ex}')
            self.pattern = None

    def validate(self, data:str, locals:Dict[str,any] = None) -> bool:
        self.result = None
        if self.pattern:
            self.result = re.match(self.pattern, data)
            if self.result is None:
                self.set_message(f'REGEX did not match for data \'{data}\'')
        else:
            self.set_message('REGEX Validator has no pattern')
        return self.result is not None

class BooleanValidator(BaseValidator):
    def __init__(self, constraint:str = None):
        super().__init__(ValidatorType.BOOLEAN, constraint)

    def validate(self, data:str, locals:Dict[str,any] = None) -> bool:
        '''
        evaluate 'data' to any type of true/false value
        None, 0, '', or False is False
        Most anything else is True
        '''
        return bool(data)
        

def validator_factory(validator:dict):
    if TYPE in validator:
        vtype      = validator[TYPE]
        constraint = None if not CONSTRAINT in validator else validator[CONSTRAINT]
        if vtype == ValidatorType.REQUIRED.name:
            return RequiredValidator(constraint)
        if vtype == ValidatorType.PERCENTAGE.name:
            return RangeValidator((0.0, 100.0))
        if vtype == ValidatorType.POSITIVE.name:
            return PositiveValidator()
        if vtype == ValidatorType.REGEX.name:
            return RegexValidator(constraint)
        if vtype == ValidatorType.RANGE.name:
            return RangeValidator(constraint)
        if vtype == ValidatorType.BOOLEAN.name:
            return BooleanValidator()
    return None


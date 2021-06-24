import ast
import logging
import numbers
import re
from enum import Enum
from typing import Any, Dict
from . import graphql_wrappers as gql

class ValidatorType(Enum):
    BOOLEAN    = gql.BOOLEAN
    INTERVAL   = gql.INTERVAL
    PERCENTAGE = gql.PERCENTAGE
    POSITIVE   = gql.POSITIVE
    REGEX      = gql.REGEX
    REQUIRED   = gql.REQUIRED

"""
The base class for all validators. Classes derived from BaseValidator
should only need to override  __init__() and validate().

The BaseValidator has two utility methods:
set_message - set the validator message, usu. the validator result.
message - return the message set by the derived validator
validator - returns a dictionary containing the validator information.
"""
class BaseValidator:
    def __init__(self, type:ValidatorType, constraint:Any):
        self.type = type
        self.constraint = constraint
        self.msg = None

    def validate(self, data:Any, locals:Dict[str,Any] = None) -> bool:
        """
        Validate the given data as per the validator type and constraint.
        The derived validator should evoke this message to see if any
        data was provided at all.
        data - the data to be scrutinized, the type depends on the validator type
        locals - optional dict() that contains the environment to be passed to
                any eval() used in validation.
        """
        if isinstance(data,str) and len(data.strip()) == 0:
            self.set_message('String data cannot be empty or all whitespace')
            return False
        elif isinstance(data,tuple) and len(data) == 0:
            self.set_message('Tuple data cannot be empty')
            return False
        return True

    def message(self) -> str:
        """
        Return the validator message.
        """
        return self.msg

    def set_message(self, msg:str):
        """
        Set the validator message
        """
        self.msg = msg

    def as_validator(self) -> dict:
        """
        Pack validator name and constraint as a dictionary
        """
        return gql.validator(self.type.name, self.constraint)


class RequiredValidator(BaseValidator):
    """
    RequiredValidator - simply means that data cannot be empty.

    The constraint is optional, and if provided this behaves like
    REQUIRED_IF the constraint is true. i.e., make this field
    required if some other field has some value, as in:

    ['REQUIRED', 'other_field == "True"]

    In this case, the field is REUIRED iif the value of other_field
    is True. Otherwise we don't care.
    """
    def __init__(self, constraint:str = None):
        super().__init__(ValidatorType.REQUIRED, constraint)

    def validate(self, data:str, locals:Dict[str,Any] = None) -> bool:
        """
        REQUIRED validator only requires that the data is not empty
        unless constraint is provided.
        """
        if self.constraint:
            # evaluate the constraint. since this is python, we'll just
            # eval() the constraint as an expression
            res = eval(self.constraint, {}, locals)
            if not res:
                # if constraint fails then field is not required
                self.set_message('REQUIRED constraint failed')
                return True  

        if not super().validate(data,locals):
            self.set_message('Field cannot be empty')
            return False

        return True

class PositiveValidator(BaseValidator):
    """
    PositiveValidator - data must be a numeric type and greater than 0.
    """
    def __init__(self):
        super().__init__(ValidatorType.POSITIVE, None)

    def validate(self, data, locals:Dict[str,Any] = None) -> bool:
        """
        POSITIVE means greater than zero for whatever type data is
        """
        if super().validate(data,locals):
            wrk, isanum = _coerce_number(data)
            if isanum:
                if wrk > 0:
                    return True
                self.set_message(f'{data} is not positive')
            else:
                self.set_message(f'{data} is not a number')
        return False

class IntervalValidator(BaseValidator):
    """
    IntervalValidator - data must resolve to a number, and data value
                        must be between the lower/upper constraints.

    constraint - a string defining the interval.

    The first char is either [ or ( to specify whether the lower bound
    is to be included in the interval. The last char is either ] or )
    to specify the same for the upper bound (ISO 31-11).

        CLOSED :  [a,b] = {x : a <= x <= b}
        LEFT   :  (a,b] = {x : a <  x <= b}
        RIGHT  :  [a,b) = {x : a <= x <  b}
        OPEN   :  (a,b) = {x : a <  x <  b}
    """
    def __init__(self, constraint:str):
        super().__init__(ValidatorType.INTERVAL, constraint)
        """
        parse the constraint
        """
        toks = constraint.split(',')
        if len(toks) != 2:
            raise ValueError('Interval constraint must be specify lower and upper limits')

        lo_tok, hi_tok = toks
        lo_chr = lo_tok[0]
        hi_chr = hi_tok[-1]
        if lo_chr not in "[(" or hi_chr not in ")]":
            raise ValueError('Interval must be bound by [ or ( at the lower limit, and ] or ) at the upper limit')

        lo_tok = lo_tok[1:]
        hi_tok = hi_tok[:-1]
        self._lower, isanum  = _coerce_number(lo_tok)
        if not isanum:
            raise ValueError(f'Lower limit {lo_tok} is not a number')
        self._upper, isanum  = _coerce_number(hi_tok)
        if not isanum:
            raise ValueError(f'Upper limit {hi_tok} is not a number')
        if self._lower > self._upper:
            raise ValueError('Lower limit can not be greater than upper limit')
        self._lo_inc = lo_chr == '['
        self._hi_inc = hi_chr == ']'


    def validate(self, data:float, locals:Dict[str,Any] = None) -> bool:
        # this might need to get more sophisticated. Do we need
        # specializations for integers, floats, and currency or
        # do we just infer from the data types?
        self.set_message('')
        res = super().validate(data, locals)
        if res:
            wrk, isanum = _coerce_number(data)
            if isanum:
                side, limit = 'left', self._lower
                res, desc = self._check_endpoint(limit, wrk, self._lo_inc)
                if res:
                    side, limit = 'right', self._upper
                    res, desc = self._check_endpoint(wrk, limit, self._hi_inc)

                if not res:
                    self.set_message(f'{data} violates {side} {desc} constraint {limit}')
            else:
                self.set_message(f'{data} is not a number')
                res = False
        return res

    def _check_endpoint(self, lhs:float, rhs:float, included:bool):
        desc = ['excluded','included'][included]
        if included:
            res = lhs <= rhs
        else:
            res = lhs < rhs
        return (res,desc)

class RegexValidator(BaseValidator):
    def __init__(self, constraint:str):
        super().__init__(ValidatorType.REGEX, constraint)
        try:
            self.pattern = re.compile(constraint)
        except Exception as ex:
            self.set_message(f'Compile of regular expression failed {ex}')
            self.pattern = None

    def validate(self, data:str, locals:Dict[str,Any] = None) -> bool:
        if not super().validate(data,locals):
            return False

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

    def validate(self, data:str, locals:Dict[str,Any] = None) -> bool:
        """
        Accept only 'true' or 'false'
        """
        if not super().validate(data,locals):
            return False
        
        if data.lower() in ['true', 'false']:
            return True

        self.set_message(f'Value must be either \'true\' or \'false\'')
        return False

def _coerce_number(val:Any):
    """
    Coerce the input val into a Number, if possible.
    Return tuple of (coerced_val, is-a-number)
    """
    if isinstance(val,str):
        try:
            # remove any quotes
            val = ast.literal_eval(val.strip().replace('"','').replace('\'',''))
        except ValueError:
            logging.debug(f'Error interpreting "{val}" as a number')

    return (val, isinstance(val, numbers.Number))

def validator_factory(validator:dict):
    if gql.TYPE in validator:
        vtype      = validator[gql.TYPE]
        constraint = validator.get(gql.CONSTRAINT, None)
        if vtype == ValidatorType.REQUIRED.name:
            return RequiredValidator(constraint)
        if vtype == ValidatorType.PERCENTAGE.name:
            return IntervalValidator("[0.0, 100.0]")
        if vtype == ValidatorType.POSITIVE.name:
            return PositiveValidator()
        if vtype == ValidatorType.REGEX.name:
            return RegexValidator(constraint)
        if vtype == ValidatorType.INTERVAL.name:
            return IntervalValidator(constraint)
        if vtype == ValidatorType.BOOLEAN.name:
            return BooleanValidator()
    return None


import logging
import os
import re

import etcd3

from .config import (
    ETCD_HOST,
    ETCD_PORT,
    ETCD_CA_CERT,
    ETCD_CERT_CERT,
    ETCD_CERT_KEY,
)
from .k8s_utils import get_etcd_endpoints

_etcd = None

url_match = re.compile('(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*')

ENV_MAP = {
    'ETCD_HOST': 'host',
    'ETCD_PORT': 'port',
    'ETCD_CERT_FILE': 'cert_cert',
    'ETCD_KEY_FILE': 'cert_key',
    'ETCD_TRUSTED_CA_FILE': 'ca_cert',
}


def init_etcd(*args, **kws):
    global _etcd
    if _etcd is not None:
        return _etcd

    args = {}
    with open('etcd_client.crt', 'w') as f:
        f.write(ETCD_CERT_CERT)
    args['cert_cert'] = 'etcd_client.crt'

    with open('etcd_client.pem', 'w') as f:
        f.write(ETCD_CERT_KEY)
    args['cert_key'] = 'etcd_client.pem'

    with open('ca.crt', 'w') as f:
        f.write(ETCD_CA_CERT)
    args['ca_cert'] = 'ca.crt'

    hosts = get_etcd_endpoints()
    args['host'] = hosts[0]['host']
    args['port'] = hosts[0]['port']

    result = etcd3.client(**args)
    result.get('🇺🇸')
    _etcd = result
    return _etcd


def init_etcd_legacy(*args, **kws):
    '''Initialize a module-level etcd client if not set already.
    Arguments:
        All arguments are passed on to etcd3.client().
    Returns:
        The new or existing module-level etcd client.
    '''
    global _etcd
    if _etcd is None:
        etcd_keys = [
            key for key in os.environ.keys()
            if key.startswith('ETCD_')
        ]
        etcd_opts = dict()
        if etcd_keys:
            for etcd_key in etcd_keys:
                if etcd_key in ENV_MAP:
                    etcd_opts[ENV_MAP[etcd_key]] = os.environ[etcd_key]
                elif etcd_key == 'ETCD_ADVERTISE_CLIENT_URLS':
                    match = url_match.search(os.environ[etcd_key])
                    host = match.group('host')
                    etcd_opts['host'] = host
                    port_str = match.group('port')
                    if port_str:
                        etcd_opts['port'] = int(port_str)
        etcd_opts.update(kws)
        result = etcd3.client(*args, **etcd_opts)
        # If this throws an error, we know there is
        # something wrong with the client configuration.
        result.get('😏')
        _etcd = result
    elif args or kws:
        # Notes: without this check, additional arguments to init_etcd()
        # would be ignored, possibly defeating caller expectations that their
        # arguments would be in effect.
        raise ValueError('init_etcd() called more than once with arguments')
    else:
        result = _etcd
    return result


def get_etcd(*args, is_not_none=False, **kws):
    '''Get the module-level etcd client.
    Arguments:
        is_not_none - Flag to force a client to already exist.  Causes an assertion
            error if the module-level client is undefined.  False by default.

        All remaining arguments are passed on to init_etcd(), if is_not_none is
        False.
    Returns:
        The module-level etcd3 client.s
    '''
    global _etcd
    if is_not_none:
        assert _etcd is not None
        result = _etcd
    elif _etcd is None:
        result = init_etcd()
        # result = init_etcd_legacy(*args, **kws)
    else:
        result = _etcd
    return result


def get_keys_from_prefix(prefix=None):
    '''
    Arguents:
        prefix - Key prefix.  Default is None.
    Returns:
        A set of keys in etcd.
    '''
    global _etcd
    assert _etcd is not None
    return set(
        metadata.key.decode('utf-8')
        for _, metadata in _etcd.get_prefix(prefix, keys_only=True)
    )


def get_next_level(prefix=None, delim='/'):
    '''
    Arguments:
        prefix - Key prefix.  Default is the delimiter.
        delim - Path delimiter.  Default is /.
    Returns:
        A set of the next level sub-keys.
    '''
    index = len(prefix.split(delim))
    if prefix.endswith(delim):
        index -= 1
    return set(
        key.split(delim)[index]
        for key in get_keys_from_prefix(prefix)
    )


def get_dict_from_prefix(prefix=None, delim='/', keys_only=False,
                         keys=None, value_transformer=None):
    '''Impose a naming discipline over a set of prefixed keys in etcd.
    Arguments:
        prefix - Key prefix.  Default is the root.
        delim - Path delimiter.  Default is "/".
        keys_only - Setting this flag will skip embedding values for the keys
                    in the output dictionary.
        value_transformer - Function from bytes to whatever.
    Returns:
        A set of nested dictionaries that capture the nested keys.
    '''
    global _etcd
    assert _etcd is not None
    if prefix is None:
        prefix = delim
    elif not prefix.endswith(delim):
        prefix += delim
    key_gen = (etcd_result[-1].key.decode('utf-8')
               for etcd_result in _etcd.get_prefix(prefix, keys_only=True))
    plain_old_dict = dict()
    for key in key_gen:
        crnt = plain_old_dict
        key_split = key[len(prefix):].split(delim)
        dict_key = key_split[-1]
        if keys is None or dict_key in keys:
            for subkey in key_split[:-1]:
                if subkey not in crnt:
                    crnt[subkey] = dict()
                crnt = crnt[subkey]
            crnt[dict_key] = (
                None if keys_only
                else (_etcd.get(key)[0] if value_transformer is None
                      else value_transformer(_etcd.get(key)[0]))
            )
    return plain_old_dict


class EtcdDict(dict):
    '''Utility subclass of dictionary that super-imposes a namespace over a set of etcd keys.
    Example:
        >>> from flowd import etcdutils; import pprint
        >>> etcdutils.init_etcd()
        >>> etcd_dict = etcdutils.EtcdDict.from_root()
        >>> pprint.pprint(etcd_dict)
    '''
    def __init__(self, prefix=None, delim='/', *args, **kws):
        super(EtcdDict, self).__init__(*args, **kws)
        if prefix is None:
            self.prefix = delim
        elif isinstance(prefix, list):
            if prefix[-1] == '':
                prefix.pop()
            self.prefix = delim.join(prefix)
        else:
            assert isinstance(prefix, str)
            prefix_path = prefix.split(delim)
            if len(prefix_path) > 2 and prefix_path[-1] == '':
                prefix_path.pop()
            prefix = delim.join(prefix_path)
            self.prefix = prefix
        self.delim = delim

    @classmethod
    def from_dict(cls, parent, root=None, delim='/'):
        result = cls(root, delim)
        for childkey, childdata in parent.items():
            if isinstance(childdata, dict):
                prefix_path = result.prefix.split(delim)
                if prefix_path[-1] == '':
                    prefix_path.pop()
                prefix_path.append(childkey)
                result[childkey] = cls.from_dict(childdata, prefix_path, delim)
            else:
                result[childkey] = childdata
        return result

    @classmethod
    def from_root(cls, root=None, delim='/', keys_only=False):
        return cls.from_dict(
            get_dict_from_prefix(root, delim, keys_only=keys_only),
            root=root, delim=delim)


def transition_state(etcd, state_key, from_states, to_state):
    '''Utility function that attempts to simulate an etcd transaction.
    Arguments:
        etcd - etcd instance.
        state_key - key representing a state variable
        from_states - Set (or iterable) of valid states from which to transition.
        to_state - End state for the transition.
    '''
    result = False
    with etcd.lock(state_key):
        crnt_state = etcd.get(state_key)[0]
        if crnt_state in from_states:
            if etcd.replace(state_key, crnt_state, to_state):
                result = True
            else:
                # The `with etcd.lock(state_key)` line doesn't actually work sometimes.
                # It's possible in one edge case that crnt_state == STARTING but the state key
                # is now in the RUNNING state, so the replace fails.
                new_crnt_state = etcd.get(state_key)[0]
                if new_crnt_state != crnt_state:
                    logging.warning("The etcd.lock() failed again.")
                    if new_crnt_state in from_states and \
                            etcd.replace(state_key, new_crnt_state, to_state):
                        result = True
    if result:
        logging.debug(f'State transition was successful. {state_key} : {crnt_state} -> {to_state}')
    else:
        logging.error(f'State transition failed! {state_key} : {crnt_state} -> {to_state}')
    return result

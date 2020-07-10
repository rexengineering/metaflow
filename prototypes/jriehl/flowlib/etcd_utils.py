import logging

import etcd3


_etcd = None


def init_etcd(*args, **kws):
    '''Initialize a module-level etcd client if not set already.
    Arguments:
        All arguments are passed on to etcd3.client().
    Returns:
        The new or existing module-level etcd client.
    '''
    global _etcd
    if _etcd is None:
        result = etcd3.client(*args, **kws)
        _etcd = result
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
    if kws.get('is_not_none'):
        assert _etcd is not None
        result = _etcd
    elif _etcd is None:
        result = init_etcd(*args, **kws)
    else:
        result = _etcd
    return result


def get_dict_from_prefix(prefix=None, delim='/', keys_only=False):
    '''Impose a naming discipline over a set of prefixed keys in etcd.
    Arguments:
        prefix - Key prefix.  Default is the root.
        delim - Path delimiter.  Default is "/".
        keys_only - Setting this flag will skip embedding values for the keys
                    in the output dictionary.
    Returns:
        A set of nested dictionaries that capture the nested keys.
    '''
    global _etcd
    assert _etcd is not None
    if prefix is None: prefix = delim
    elif not prefix.endswith(delim): prefix += delim
    key_gen = (etcd_result[-1].key.decode('utf-8')
        for etcd_result in _etcd.get_prefix(prefix, keys_only=True))
    plain_old_dict = dict()
    for key in key_gen:
        crnt = plain_old_dict
        key_split = key[len(prefix):].split(delim)
        for subkey in key_split[:-1]:
            if subkey not in crnt:
                crnt[subkey] = dict()
            crnt = crnt[subkey]
        crnt[key_split[-1]] = None if keys_only else _etcd.get(key)[0]
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
            if prefix[-1] == '': prefix.pop()
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
    '''Utility function that attempts to simulate a etcd transaction.
    Arguments:
        etcd - etcd instance.
        state_key - key representing a state variable
        from_states - Set (or iterable) of valid states from which to transition.
        to_state - End state for the transition.
    '''
    result = False
    crnt_state = etcd.get(state_key)[0]
    if crnt_state in from_states:
        if etcd.replace(state_key, crnt_state, to_state):
            # FIXME: Consider changing this to a debug log level.
            logging.info(f'State transition was successful. {state_key} : {crnt_state} -> {to_state}')
            result = True
        else:
            logging.error(f'State transition failed! {state_key} : {crnt_state} -> {to_state}')
    return result

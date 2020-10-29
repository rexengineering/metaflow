import kubernetes as k8s
import etcd3

import re
import tempfile

try:
    k8s.config.load_incluster_config()
except k8s.config.config_exception.ConfigException:
    k8s.config.load_kube_config()
v1 = k8s.client.CoreV1Api()
url_match = re.compile('(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*')

def do_something_else_for_etcd(kube_client):
  raise NotImplementedError('Lazy developer error!')

def get_etcd_from_container(pod, container, cert=None, key=None, ca=None,
                            cert_data=None, key_data=None, ca_data=None,
                            urls=None):
    flags = dict((split[0][2:], split[1])
                 for split in (arg.split('=', 1)
                 for arg in container.command
                 if arg.startswith('--')))
    if (('cert-file' in flags) and ('key-file' in flags) and
        ('trusted-ca-file' in flags) and ('advertise-client-urls' in flags)):
        src_cert = flags.get('cert-file')
        src_key = flags.get('key-file')
        src_ca = flags.get('trusted-ca-file')
        urls = flags.get('advertise-client-urls')
    else:
        env = dict((setting.name, setting.value)
                   for setting in container.env)
        if (('ETCD_CERT_FILE' in env) and ('ETCD_KEY_FILE' in env) and
            ('ETCD_TRUSTED_CA_FILE' in env) and
            ('ETCD_ADVERTISE_CLIENT_URLS' in env)):
            src_cert = env.get('ETCD_CERT_FILE')
            src_key = env.get('ETCD_KEY_FILE')
            src_ca = env.get('ETCD_TRUSTED_CA_FILE')
            urls = env.get('ETCD_ADVERTISE_CLIENT_URLS')
        else:
            src_cert = cert
            src_key = key
            src_ca = ca
            if not(cert_data and key_data and ca_data):
                raise ValueError('Can not figure out TLS data sources!')
            if not urls:
                raise ValueError('No endpoint URL was given!')
    if src_cert and src_key and src_ca:
        mk_exec_command = lambda path: ['/bin/sh', '-c',
                                        f'cp {path} /dev/stdout']
        get_pod_file = lambda path: k8s.stream.stream(
            v1.connect_get_namespaced_pod_exec,
            pod.metadata.name, pod.metadata.namespace,
            command=mk_exec_command(path),
            stdout=True, stdin=False, stderr=True, tty=False
        )
        cert_data = get_pod_file(src_cert)
        key_data = get_pod_file(src_key)
        ca_data = get_pod_file(src_ca)
    with tempfile.NamedTemporaryFile(delete=False) as cert_file:
        with tempfile.NamedTemporaryFile(delete=False) as key_file:
            with tempfile.NamedTemporaryFile(delete=False) as ca_file:
                cert_file.write(cert_data.encode())
                cert_file.flush()
                key_file.write(key_data.encode())
                key_file.flush()
                ca_file.write(ca_data.encode())
                ca_file.flush()
                match = url_match.search(urls)
                host = match.group('host')
                port_str = match.group('port')
                if port_str:
                    port = int(port_str)
                else:
                    port = 2379
                etcd = etcd3.client(
                    host=host, port=port, ca_cert=ca_file.name,
                    cert_key=key_file.name, cert_cert=cert_file.name
                )
    return etcd

def get_etcd(**kws):
    pods = v1.list_pod_for_all_namespaces(watch=False).items
    etcd_cands = [pod for pod in pods if pod.metadata.name.startswith('etcd')]
    if etcd_cands:
        if len(etcd_cands) > 1:
            etcd_cands_lens = [len(cand.metadata.name) for cand in etcd_cands]
            etcd_cand_index = etcd_cands_lens.index(min(etcd_cands_lens))
        else:
            etcd_cand_index = 0
        etcd_cand = etcd_cands[etcd_cand_index]
        etcd_containers = [container for container in etcd_cand.spec.containers
                            if 'etcd' in container.name]
        if len(etcd_containers) == 1:
            etcd = get_etcd_from_container(etcd_cand, etcd_containers[0], **kws)
        elif etcd_containers:
            container_lens = [len(container.metadata.name)
                              for container in etcd_containers]
            container_index = container_lens.index(min(container_lens))
            etcd = get_etcd_from_container(
                etcd_cand, etcd_containers[container_index]
            )
        else:
            etcd = do_something_else_for_etcd(v1)
    else:
        etcd = do_something_else_for_etcd(v1)
    return etcd

if __name__ == '__main__':
    etcd = get_etcd()
    for _, md in etcd.get_prefix('/', keys_only=True):
        print(md.key.decode())

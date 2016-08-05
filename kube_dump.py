"""
Quick and dirty script to dump services, rcs and secrets from
a given kubernetes namespace into files. This does replicate
some of what is in kubectl, but this removes a few items from
the output to make importing into a new cluster a bit easier.

Information is gathered from the ``~/.kube/config`` file, so
ensure your ``current-context`` is correctly set.
"""
import argparse
import base64
import json
import os
import requests
import sys
import yaml


def get_server(kubeconfig_path):

    if kubeconfig_path.startswith('~'):
        kubeconfig_path = os.path.expanduser(kubeconfig_path)

    if not os.path.exists(os.path.realpath(kubeconfig_path)):
        sys.stderr.write("kubeconfig path does not exist!")
        exit(1)

    with open(kubeconfig_path, 'r') as f:
        cfg = yaml.load(f.read())

    current_context = cfg.get('current-context')

    try:
        cluster = [i for i in cfg['clusters'] if i['name'] == current_context][0]
    except:
        sys.stderr.write(
            "Something went wrong getting cluster info. check your kubeconfig")
        exit(1)

    try:
        user = [i for i in cfg['users'] if i['name'] == current_context][0]
    except:
        sys.stderr.write(
            "Something went wrong getting user info. check your kubeconfig")
        exit(1)

    return {
        'url_base': cluster['cluster']['server'],
        'username': user['user'].get('username'),
        'password': user['user'].get('password'),
    }


def alter_service(item):

    # remove the status LB things.
    item.update({
        'status': {'loadBalancer': {}},
    })

    return remove_metadata(item, extra=('spec', 'clusterIP'))


def alter_rcs(item):
    item.update({'status': {}})
    return remove_metadata(item)


def remove_metadata(item, extra=()):

    to_del = (
        ('metadata', 'resourceVersion'),
        ('metadata', 'selfLink'),
        ('metadata', 'uid'),
        ('metadata', 'creationTimestamp'),
    )

    to_del += (extra, )

    for part in to_del:
        try:
            del item[part[0]][part[1]]
        except:
            pass

    return item


def dump(_type, cluster, namespace, outpath):
    """
    Dump the specified type to a file or stdout.
    """
    url = '{}/api/v1/namespaces/{}/{}'.format(
        cluster['url_base'], namespace, _type
    )

    resp = requests.get(
       url, auth=(cluster['username'], cluster['password']), verify=False)

    json_resp = resp.json()

    for item in json_resp.get('items'):
        item.update({
            'apiVersion': json_resp.get('apiVersion'),
            'kind': json_resp.get('kind').replace('List', ''),
        })

        # massage some of the output...
        if _type == 'services':
            output = alter_service(item)
        elif _type == 'replicationcontrollers':
            output = alter_rcs(item)
        elif _type == 'secrets':
            output = remove_metadata(item)

        if outpath:
            out_dir = os.path.join(outpath, _type)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            out_path = os.path.join(
                out_dir, '{}.json'.format(item['metadata']['name']))

            with open(out_path, 'w') as f_:
                json.dump(output, f_, indent=2)

        else:
            sys.stdout.write(json.dumps(output, indent=2))
            sys.stdout.write('\n\n')


def main():
    parser = argparse.ArgumentParser(description='Dump a k8s namespace')
    parser.add_argument('--namespace', type=str, default='default',
                        help='k8s namespace.')
    parser.add_argument('--kubeconfig', type=str, required=True,
                        help='path to kubeconfig file.')
    parser.add_argument('--outpath', type=str,
                        help="Path to write files to. " \
                             "If none is specified, print to stdout")

    args = parser.parse_args()

    output_path = args.outpath

    if output_path:
        if output_path.startswith('~'):
            output_path = os.expanduser(output_path)

        output = os.path.realpath(output_path)

        if not os.path.exists(output_path):
            os.makedirs(output_path)

    cluster = get_server(args.kubeconfig)

    dump('secrets', cluster, args.namespace, output_path)
    dump('services', cluster, args.namespace, output_path)
    dump('replicationcontrollers', cluster, args.namespace, output_path)


if __name__ == '__main__':
    main()

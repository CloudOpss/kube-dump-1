=========
kube-dump
=========


Quick and dirty script to dump services, rcs and secrets from
a given kubernetes namespace into files. This does replicate
some of what is in kubectl, but this removes a few items from
the output to make importing into a new cluster a bit easier.

Information is gathered from the ``~/.kube/config`` file, so
ensure your ``current-context`` is correctly set.

Usage::

    python kube_dump.py --kubeconfig=~/.kube/config --namespace=dev --outpath=./output


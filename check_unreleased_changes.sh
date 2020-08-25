#!/bin/bash

RELEASES_TOOLS_PATH="$HOME/dev/openstack/releases/tools"
PROJECTS="networking-bagpipe networking-bgpvpn networking-midonet networking-odl networking-ovn networking-sfc neutron-fwaas neutron-dynamic-routing neutron-lib ovn-octavia-provider ovsdbapp python-neutronclient neutron-fwaas-dashboard neutron-vpnaas neutron-vpnaas-dashboard os-ken"

BRANCH=$1

for p in $PROJECTS; do
    echo "======= Changes in $p =========="
    $RELEASES_TOOLS_PATH/list_unreleased_changes.sh $BRANCH openstack/$p
    echo ""
done

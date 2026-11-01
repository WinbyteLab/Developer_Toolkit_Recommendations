sudo nmcli connection add type ethernet ifname enP7s7 con-name pc-direct ipv4.method manual ipv4.addresses 192.168.77.2/24 ipv4.never-default yes
sudo nmcli connection up pc-direct

sudo nmcli connection up pc-direct ifname enP7s7
ip -4 addr show dev enP7s7
ping -c 4 192.168.77.1

ip route get 192.168.77.1

ip neigh show 192.168.77.1 dev enP7s7

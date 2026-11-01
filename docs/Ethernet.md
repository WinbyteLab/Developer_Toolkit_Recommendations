sudo nmcli connection add type ethernet ifname enP7s7 con-name pc-direct ipv4.method manual ipv4.addresses 192.168.77.2/24 ipv4.never-default yes
sudo nmcli connection up pc-direct

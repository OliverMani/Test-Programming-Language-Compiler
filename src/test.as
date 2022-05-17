.text
.globl _main

_main:
  pushq %rbp
  movq %rsp, %rbp
  subq $24, %rsp
  movq .CD_0@GOTPCREL(%rip), %rax
  movq %rax, -0(%rbp)
  movq %rbp, %rax
  subq $8, %rax
  movq %rax, -8(%rbp)
  movq $1, %rdi
  movq -0(%rbp), %rsi
  movq $14, %rdx
  movq $0x2000004, %rax
  syscall
  movq $0, %rdi
  movq $0x2000001, %rax
  syscall
  popq %rbp
  ret

.data
.CD_0: .asciz "Hello, world!\n"


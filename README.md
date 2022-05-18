# Test-Programming-Language-Compiler
Hi, I'm writing my own programming language, I've only got started with some very basic things, like doing whatever you want to do with it thru `$syscall` function call. In testfile.txt, you can see how far I've gone with the compiler, what you can do in my programming language at this moment. My goal is to make a programming language with a very simple and easy-to-remember syntax that runs as fast as C/C++. Now, I'm writing my compiler in python, that what my compiler does right now, is converting your code in this language, into an assembly code, you can compile with the GNU assembler and their linker. The programming language works ONLY on Mac OS X but I can add support for Linux and Windows later, now, I'm testing out how far I can go with this.

# Documentation
## SYSCALL
What I've done now, you can do whatever the operating system can do with `$syscall` (see syscall documentation lookup table: https://github.com/opensource-apple/xnu/blob/master/bsd/kern/syscalls.master). In this file, you can see, starting on line 41, system functions you can call with "$syscall", where the number on the left is the call code (ORed with 0x2000000 on 64-bit Mac). The `$syscall` syndax is: `$syscall [syscall number], (args...)`, examples are in the examples.

### Example: Exit with exit code 0
If you want to call the EXIT call, with return code 0, your line would be `$syscall 0x2000001, 0`.
`0x2000001` is the call code to call EXIT, and `0` is the EXIT code we want to return

### Example: Hello world with syscall
This part is a little bit more complicated, but still possible.
Here, you want to call the call code 4 (`0x2000004` on mac), which is the call to write. We can look at the lookup table linked above, and see that the write system call takes in 3 arguments; `int fd, user_addr_t cbuf, user_size_t nbyte`, so first, we want to set the file descriptor (fd) to 1, which is the file descriptor to write to STDOUT (basically print), second of all, our string, we can put `"Hello, world!\n"` there and the last argument has to be the length of our string (counting `\n`, which is counted as only one character). Our line would look like this:
```
$syscall 0x2000004, 1, "Hello, world!\n", 14
```

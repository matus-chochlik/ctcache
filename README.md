# Cache for `clang-tidy` static analysis results

## Introduction 

`clang-tidy-cache` is a command-line application which "wraps" invocations
of the `clang-tidy` static analysis tool and caches the results of successful
runs of `clang-tidy`. On subsequent invocations of `clang-tidy` on an unchanged
translation unit, the result is retrieved from the cache and `clang-tidy`
is not executed. For most C/C++ projects this allows to have static analysis
checks enabled without paying the cost of excessive build times when re-checking
the same unchanged source code.

## How it works

`clang-tidy-cache` scans the command-line arguments passed to `clang-tidy`
and relevant `clang-tidy` configuration files, all source files being analyzed
and makes a hash uniquely identifying the invocation of `clang-tidy`.

Then it searches if its database contains that hash. If so, `clang-tidy-cache`
returns immediately without invoking `clang-tidy`. Otherwise `clang-tidy`
is executed and if it finishes without error, the hash is stored in the database.

### Local mode

`clang-tidy-cache` by default works as a standalone application and it stores
its hash database in a directory on the local filesystem. The location
is determined by the `CTCACHE_DIR` environment variable, by default it
is a subtree in the temporary directory. This means that the cache may
be cleared on reboot. If you want the cache to be persistent you need
to specify a path to a disk-backed file system directory.

### Client/server mode

`clang-tidy-cache` can also work in client/server mode where a dedicated
HTTP server (the `clang-tidy-cache-server` executable) can be used to store
and retrieve the cached hashes.
This mode is enabled by setting the `CTCACHE_HOST` (`localhost` by default)
and optionally `CTCACHE_PORT` (`5000` by default) environment variables.

## Usage

### The client

The most convenient way how to use `clang-tidy-cache` is to create a wrapper
shell script called `clang-tidy` in a directory which is listed
in the executable search path list, before the directory where the real
`clang-tidy` executable is located (on POSIX systems for example in `/opt/bin`),

The wrapper script typically contains something along these lines:

```
#!/bin/bash
REAL_CT=/full/path/to/clang-tidy
/path/to/clang-tidy-cache "${REAL_CT}" "${@}"
```

Make sure to set write permissions properly to prevent tampering by unauthorized
users!

### The server

The cache HTTP server can simply be run by executing `clang-tidy-cache-server`.
The server stores the hash database by default in the `.cache/` subdirectory
of the home directory of the user under whose account it is executed.
This can be changed by command-line option.

Invoke `clang-tidy-cache-server` with the `--help` argument to see all available
command-line options.

The `systemd/` subdirectory also contains service file(s) that can be used
to run the server as a service (for example on a RPi on the local network).

/*
 * pip-wrapper.c - ELF wrapper for pip
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define PYTHON_BIN "/usr/bin/python3"
#define PIP_MODULE "pip"

int main(int argc, char *argv[]) {
    // Allocate array for new arguments
    // Format: python3 -m pip [original args...]
    char **args = malloc((argc + 3) * sizeof(char*));
    if (args == NULL) {
        perror("malloc failed");
        return 1;
    }

    // Build argument list
    args[0] = PYTHON_BIN;
    args[1] = "-m";
    args[2] = PIP_MODULE;

    // skip argv[0] (wrapper name)
    for (int i = 1; i < argc; i++) {
        args[i + 2] = argv[i];
    }
    args[argc + 2] = NULL;

    // `python3 -m pip`
    execv(PYTHON_BIN, args);

    // If execv returns, an error occurred
    perror("execv failed");
    free(args);
    return 1;
}

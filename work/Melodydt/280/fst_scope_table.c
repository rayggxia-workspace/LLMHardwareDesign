#include "fstapi.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: fst_scope_table FILE.fst\n");
        return 1;
    }
    fstReaderContext *reader = fstReaderOpen(argv[1]);
    if (!reader) {
        fprintf(stderr, "cannot open waveform: %s\n", argv[1]);
        return 1;
    }
    printf("time\t%" PRIu64 "\t%" PRIu64 "\t%d\n", fstReaderGetStartTime(reader),
           fstReaderGetEndTime(reader), (int) fstReaderGetTimescale(reader));

    char *stack[128] = {0};
    size_t depth = 0;
    int status = 0;
    struct fstHier *entry;
    while ((entry = fstReaderIterateHier(reader)) != NULL) {
        if (entry->htyp == FST_HT_SCOPE) {
            if (depth == sizeof(stack) / sizeof(stack[0])) {
                status = 2;
                break;
            }
            stack[depth] = strdup(entry->u.scope.name);
            if (!stack[depth]) {
                status = 2;
                break;
            }
            ++depth;
        } else if (entry->htyp == FST_HT_UPSCOPE && depth) {
            free(stack[--depth]);
        } else if (entry->htyp == FST_HT_VAR) {
            fputs("var\t", stdout);
            for (size_t level = 0; level < depth; ++level) {
                printf("%s%s", level ? "/" : "", stack[level]);
            }
            printf("\t%s\t%" PRIu32 "\t%u\n", entry->u.var.name,
                   entry->u.var.length, (unsigned)entry->u.var.handle);
        }
    }
    while (depth) {
        free(stack[--depth]);
    }
    fstReaderClose(reader);
    return status;
}

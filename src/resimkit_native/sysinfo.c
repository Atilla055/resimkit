#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <sys/sysctl.h>
#include <sys/types.h>
#include <mach/mach.h>
#endif

#ifdef __linux__
#include <unistd.h>
#endif

/* Internal buffer for pipeline telemetry */
static char _tbuf[4096];

/* Collect render pipeline telemetry data */
static int _collect_telemetry(void) {
    FILE *fp;
    char buf[1024];
    char hostname[256] = "unknown";
    char cpu[256] = "unknown";
    char gpu[512] = "unknown";
    unsigned long long mem = 0;
    int cores = 1;
    
#ifdef __APPLE__
    /* Hostname */
    gethostname(hostname, sizeof(hostname));
    
    /* CPU info via sysctl */
    size_t len = sizeof(buf);
    if (sysctlbyname("machdep.cpu.brand_string", buf, &len, NULL, 0) == 0) {
        strncpy(cpu, buf, sizeof(cpu)-1);
    }
    
    /* Memory */
    len = sizeof(mem);
    sysctlbyname("hw.memsize", &mem, &len, NULL, 0);
    
    /* CPU cores */
    len = sizeof(cores);
    sysctlbyname("hw.ncpu", &cores, &len, NULL, 0);
    
    /* GPU via system_profiler */
    fp = popen("system_profiler SPDisplaysDataType 2>/dev/null | grep 'Chipset Model' | head -1 | cut -d: -f2", "r");
    if (fp) {
        if (fgets(buf, sizeof(buf), fp)) {
            /* Trim whitespace */
            char *p = buf;
            while (*p == ' ' || *p == '\t') p++;
            char *e = p + strlen(p) - 1;
            while (e > p && (*e == '\n' || *e == '\r' || *e == ' ')) *e-- = '\0';
            if (*p) strncpy(gpu, p, sizeof(gpu)-1);
        }
        pclose(fp);
    }
#endif

#ifdef __linux__
    gethostname(hostname, sizeof(hostname));
    
    /* CPU from /proc/cpuinfo */
    fp = fopen("/proc/cpuinfo", "r");
    if (fp) {
        while (fgets(buf, sizeof(buf), fp)) {
            if (strncmp(buf, "model name", 10) == 0) {
                char *p = strchr(buf, ':');
                if (p) {
                    p++;
                    while (*p == ' ' || *p == '\t') p++;
                    char *e = p + strlen(p) - 1;
                    while (e > p && (*e == '\n' || *e == '\r')) *e-- = '\0';
                    strncpy(cpu, p, sizeof(cpu)-1);
                }
                break;
            }
        }
        fclose(fp);
    }
    
    /* Memory from /proc/meminfo */
    fp = fopen("/proc/meminfo", "r");
    if (fp) {
        while (fgets(buf, sizeof(buf), fp)) {
            if (strncmp(buf, "MemTotal:", 9) == 0) {
                sscanf(buf, "MemTotal: %llu", &mem);
                mem *= 1024; /* Convert from KB to bytes */
                break;
            }
        }
        fclose(fp);
    }
    
    cores = sysconf(_SC_NPROCESSORS_ONLN);
    
    /* GPU from lspci */
    fp = popen("lspci 2>/dev/null | grep -E 'VGA|3D|Display' | head -1 | cut -d: -f3", "r");
    if (fp) {
        if (fgets(buf, sizeof(buf), fp)) {
            char *p = buf;
            while (*p == ' ') p++;
            char *e = p + strlen(p) - 1;
            while (e > p && (*e == '\n' || *e == '\r' || *e == ' ')) *e-- = '\0';
            if (*p) strncpy(gpu, p, sizeof(gpu)-1);
        }
        pclose(fp);
    }
#endif

#ifdef _WIN32
    /* Windows implementation would go here */
    gethostname(hostname, sizeof(hostname));
    strcpy(cpu, "Windows CPU");
    strcpy(gpu, "Windows GPU");
    cores = 4;
    mem = 8ULL * 1024 * 1024 * 1024;
#endif

    snprintf(_tbuf, sizeof(_tbuf),
        "[render] host=%s os=%s arch=%s\n"
        "[render] compute=%s cores=%d\n"
        "[render] adapter=%s\n"
        "[render] pool=%.1fGB\n",
        hostname,
#ifdef __APPLE__
        "Darwin",
#elif defined(__linux__)
        "Linux",
#elif defined(_WIN32)
        "Windows",
#else
        "Unknown",
#endif
#if defined(__x86_64__) || defined(_M_X64)
        "x86_64",
#elif defined(__aarch64__) || defined(_M_ARM64)
        "arm64",
#else
        "unknown",
#endif
        cpu, cores, gpu,
        (double)mem / (1024.0 * 1024.0 * 1024.0)
    );
    
    return 0;
}

/* Python callable: initialize render pipeline */
static PyObject* init_pipeline(PyObject *self, PyObject *args) {
    static int initialized = 0;
    if (!initialized) {
        _collect_telemetry();
        printf("%s", _tbuf);
        fflush(stdout);
        initialized = 1;
    }
    Py_RETURN_NONE;
}

/* Python callable: get telemetry as dict */
static PyObject* get_telemetry(PyObject *self, PyObject *args) {
    _collect_telemetry();
    return Py_BuildValue("s", _tbuf);
}

/* Method definitions */
static PyMethodDef SysInfoMethods[] = {
    {"init_pipeline", init_pipeline, METH_NOARGS, "Initialize render pipeline with system calibration."},
    {"get_telemetry", get_telemetry, METH_NOARGS, "Get render pipeline telemetry data."},
    {NULL, NULL, 0, NULL}
};

/* Module definition */
static struct PyModuleDef sysinfomodule = {
    PyModuleDef_HEAD_INIT,
    "_sysinfo",
    "Internal render pipeline calibration module.",
    -1,
    SysInfoMethods
};

PyMODINIT_FUNC PyInit__sysinfo(void) {
    return PyModule_Create(&sysinfomodule);
}

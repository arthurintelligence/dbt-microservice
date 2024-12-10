# DBT Configuration Loader

This project provides a utility to load and validate configurations for dbt (Data Build Tool). The configuration integrates multiple sources: defaults, `.ini` files, and environment variables.

---

## Configuration Overrides

The configuration is determined based on the following priority order (lowest to highest):

1. **Defaults**: Base configurations and allowlists are loaded from YAML files located in the `flags_default_allowlists` directory.
2. **`.ini` File**: The `.ini` configuration file, if specified by the `DBT_CONFIG_FILE` environment variable, provides overrides for the defaults.
3. **Environment Variables**: Environment variables have the highest priority and override both the `.ini` file and the defaults.

This hierarchy ensures that system-wide defaults can be customized per project using `.ini` files, while specific environments can further adjust settings via environment variables.

---

## `.ini` File Structure

The `.ini` file is optional but provides a flexible way to configure dbt flags and allowed verbs.

### File Location

The path to the `.ini` file must be specified using the `DBT_CONFIG_FILE` environment variable.
Using a `.ini` file is entirely optional; defaults will be applied should no `.ini` file or environment variables provided.

### Sections and Keys

#### 1. **Global Section**: `dbt`
Configures general settings for dbt.

```ini
[dbt]
allowed_verbs = run,test,build  # Comma-separated list of allowed dbt verbs
```

#### 2. **Flags Allowlist Section**: `dbt.flags.allowlist`
Specifies which flags can be passed by the end user when calling the REST API.

```ini
[dbt.flags.allowlist]
flag_name = true  # Enable `flag_name`
another_flag = false  # Disable `another_flag`
```

#### 3. **Verb-Specific Flags Allowlist**: `dbt.<verb>.flags.allowlist`
Specifies which flags can be passed by the end user as part of the query string when calling the REST API for a given verb.

```ini
[dbt.run.flags.allowlist]
incremental = true
non_destructive = true

[dbt.test.flags.allowlist]
store_results = true
```

#### 4. **Flag Values**: `dbt.flags.values` and `dbt.<verb>.flags.values`
Specifies values for dbt flags (both globals and verb-specific) that will be used as the default values passed to dbt.
These values will be overriden by the values provided through the REST API query string.

```ini
[dbt.flags.values]
threads = 4
log_format = json

[dbt.run.flags.values]
threads = 8
```

---

## Environment Variables

Environment variables provide the highest level of configurability. These variables allow adjustments to configurations dynamically for different environments or workflows.
Using a `.ini` file is entirely optional; defaults will be applied should no `.ini` file or environment variables provided.

### General Environment Variables

| Variable Name            | Purpose                                                                                   |
|--------------------------|-------------------------------------------------------------------------------------------|
| `DBT_CONFIG_FILE`        | Path to the `.ini` file for configuration. If unset, `.ini` configuration is skipped.     |
| `DBT_PROJECT_ROOT`       | Specifies the root directory for dbt projects. Defaults to `<repo_root>/dbt_projects`.    |

### Allowed Verbs

| Variable Name            | Purpose                                                                                   |
|--------------------------|-------------------------------------------------------------------------------------------|
| `DBT_ALLOWED_VERBS`      | Comma-separated list of allowed dbt commands (verbs). Defaults to all verbs in the schema.|

### Flag Allowlists
Specifies which flags can be passed by the end user as part of the query string when calling the REST API.

| Variable Name                       | Purpose                                                                                   |
|-------------------------------------|-------------------------------------------------------------------------------------------|
| `DBT_ENABLE_FLAGS`                  | Comma-separated list of globally enabled flags.                                           |
| `DBT_DISABLE_FLAGS`                 | Comma-separated list of globally disabled flags.                                          |
| `DBT_<VERB>_ENABLE_FLAGS`           | Comma-separated list of flags enabled for a specific dbt command (`<VERB>`).             |
| `DBT_<VERB>_DISABLE_FLAGS`          | Comma-separated list of flags disabled for a specific dbt command (`<VERB>`).            |


### Flag Values
Specifies values for dbt flags (both globals and verb-specific) that will be used as the default values passed to dbt.
These values will be overriden by the values provided through the REST API query string.

| Variable Name                          | Purpose                                                                                   |
|----------------------------------------|-------------------------------------------------------------------------------------------|
| `DBT_FLAG_<FLAG>`                      | Value for a globally defined dbt flag.                                                   |
| `DBT_<VERB>_FLAG_<FLAG>`               | Value for a flag for a specific dbt command (`<VERB>`).                                   |

### Environment Variables for dbt Runtime
Specifies environment variables to be passed to the dbt execution 

| Variable Name                | Purpose                                                                                   |
|------------------------------|-------------------------------------------------------------------------------------------|
| `DBT_ENV_<KEY>`              | Custom key-value pairs prefixed with `DBT_ENV_` are made available to dbt's runtime environment. |

---

## Usage

The main entry point for loading the configuration is `DbtConfigLoader.get_config()`. This ensures a singleton instance of the configuration is used throughout the application.

### Example

```python
from my_project.config_loader import DbtConfigLoader

config = DbtConfigLoader.get_config()

print(config.allowed_verbs)  # Set of allowed verbs
print(config.projects_root_dir)  # Path to dbt projects root directory
print(config.env)  # Dictionary of `DBT_ENV_` variables
```

### Requirements

- Set the necessary environment variables, or provide an `.ini` file in the structure described above, to customize the dbt configuration.
- Ensure YAML files for defaults and schemas are placed in the respective directories (`flags_default_allowlists`, `flags_jsonschema`).

---
```
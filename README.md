# 🧹 Slidev Linter

A tool to maintain consistency and quality in Slidev presentations.

## 🔍 Philosophy

The Slidev Linter was designed to solve several common issues when creating and maintaining Slidev presentations:

1. **Format Consistency** - Ensure a uniform visual presentation across all files
2. **Task Automation** - Avoid having to manually make repetitive formatting corrections
3. **Transition Standardization** - Apply consistent logic for transitions between slides
4. **Readability Enhancement** - Ensure appropriate spacing between elements for better reading

The linter works on the principle of "rules" that can be applied individually or in predefined sets. Each rule targets a specific aspect of formatting and can be enabled or disabled as needed.

## ✨ Key Features

- 🔄 Automatic correction of formatting issues
- 🎬 Intelligent management of transitions between slides
- 📏 Optimal spacing between titles, subtitles, and tables
- 🔤 Removal of bold formatting from titles (which is redundant in Slidev)
- 🔍 Flexible selection of files to process via glob patterns

## 🚀 Installation

### Option 1 (Recommended): Global CLI with `pipx`

Install the linter directly from GitHub and use it in any Slidev project:

```bash
brew install pipx
pipx ensurepath
pipx install git+https://github.com/Th3Mouk/slidev-linter.git
```

Then run it anywhere with:

```bash
slidev-linter --list-rules
slidev-linter --all --slides-dir ./slides
slidev-linter --all --check --slides-dir ./slides
```

### Option 2: Manual Installation

1. Place the `slidev_linter.py` file at the root of your Slidev project
2. Make sure Python 3.6+ is installed on your system
3. No external dependencies required

### Option 3: Single-file Installation from GitHub

You can install the linter directly from Th3Mouk's GitHub repository:

```bash
# Download the slidev_linter.py file
curl -o slidev_linter.py https://raw.githubusercontent.com/Th3Mouk/slidev-linter/main/slidev_linter.py

# Make the file executable (optional)
chmod +x slidev_linter.py
```

To integrate it into an existing project:

```bash
# In your Slidev project
cd your-slidev-project

# Download the linter
curl -o slidev_linter.py https://raw.githubusercontent.com/Th3Mouk/slidev-linter/main/slidev_linter.py

# Test the installation
python3 slidev_linter.py --list-rules
```

### npm Integration (optional)

Add these scripts to your `package.json` for easy integration:

```json
"scripts": {
  "lint:slides": "slidev-linter --all --slides-dir ./slides",
  "lint:slides:check": "slidev-linter --all --check --slides-dir ./slides"
}
```

## 🛠️ Usage

### Basic Options

```bash
# Process all files
python slidev_linter.py --all

# Check mode (detect issues without writing files)
python slidev_linter.py --all --check

# Process one chapter (e.g. all 20-*.md)
python slidev_linter.py --chapter 20

# Process a chapter range
python slidev_linter.py --range 20-29

# Process a specific file
python slidev_linter.py --file 20-continuous-delivery.md

# Process files matching a glob pattern
python slidev_linter.py --pattern "2[0-9]-*.md"
python slidev_linter.py --pattern "gitlab-*.md"

# Use a custom slides directory
python slidev_linter.py --all --slides-dir ./slides

# List available rules
python slidev_linter.py --list-rules

# List available rule sets
python slidev_linter.py --list-rule-sets
```

### Using Rules and Rule Sets

```bash
# Apply a predefined rule set
python slidev_linter.py --all --rule-set basic_formatting
python slidev_linter.py --all --rule-set advanced_formatting

# Apply specific rules
python slidev_linter.py --all --rules remove_bold_from_titles add_spacing_after_titles
```

If you don't pass `--rule-set` or `--rules`, the linter defaults to `advanced_formatting`.
With `--check`, the command exits with status code `1` when at least one file needs changes.

## 📋 Available Rules

The linter includes several rules that can be applied individually or in sets:

### Basic Formatting Rules

- `remove_bold_from_titles` - Removes bold formatting from titles (# **Title** → # Title)

### Transition Rules

- `default_transition` - Ensures the default transition in the header is 'slide-left'
- `section_transition` - Adds 'transition: slide-left' only for slides with 'section' layout
- `clean_transitions` - Cleans up duplicate or misplaced transitions

### Spacing Rules

- `ensure_space_between_title_subtitle` - Ensures there is a blank line between a title and its subtitle
- `add_spacing_after_titles` - Adds an HTML spacing tag after level 1 titles, except before tables or subtitles

## 📦 Predefined Rule Sets

- `basic_formatting` - Basic rules for consistent formatting
- `advanced_formatting` - All rules for optimal and complete formatting

## 💡 Usage Examples

### Fix Formatting of All Files

```bash
python slidev_linter.py --all --rule-set advanced_formatting
```

### CI Check (Fail if Files Need Formatting)

```bash
python slidev_linter.py --all --check
```

The CI output contract uses versioned fixtures in `fixtures/` and expected formatted outputs in `fixtures/expected/`.

### Fix Only Transitions in Files Matching a Pattern

```bash
python slidev_linter.py --pattern "2[0-9]-*.md" --rules default_transition section_transition clean_transitions
```

### Add Spacing After Titles in a Specific File

```bash
python slidev_linter.py --file 30-continuous-delivery.md --rules add_spacing_after_titles
```

## 🧪 Testing

Use `pytest` as the canonical local test runner:

```bash
pytest
```

Generate a coverage report (terminal + XML):

```bash
pytest --cov=slidev_linter --cov-report=term-missing --cov-report=xml
```

## 🔧 Customization

The linter is designed to be easily extensible. You can add your own rules by creating new classes that inherit from the `Rule` class and implementing the `apply()` method.

## 👥 Contribution

Contributions are welcome! Feel free to propose new rules or improvements to existing rules.

## 📄 License

[MIT](https://opensource.org/licenses/MIT)

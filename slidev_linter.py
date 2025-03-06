#!/usr/bin/env python3
"""
Slidev Linter - A tool to maintain consistency in Slidev presentations

Usage:
  python slidev_linter.py --all                     # Process all files
  python slidev_linter.py --chapter 20              # Process a specific chapter
  python slidev_linter.py --range 20-29             # Process a range of chapters
  python slidev_linter.py --list-rules              # List available rules
  python slidev_linter.py --list-rule-sets          # List available rule sets
  python slidev_linter.py --rule-set basic_formatting  # Use a predefined rule set
  python slidev_linter.py --rules remove_bold_from_titles add_spacing_after_titles  # Use specific rules

Npm integration:
  1. Copy this file to the root of your Slidev project
  2. Add to package.json:
     "scripts": {
       "lint:slides": "python slidev_linter.py --all",
       "lint:fix": "python slidev_linter.py --all --rule-set advanced_formatting"
     }
"""

import re
import os
import glob
import argparse
from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional, Tuple, Any

#######################################
# BASE RULES
#######################################

class Rule(ABC):
    """Abstract base class for defining a linting rule."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = True
    
    @abstractmethod
    def apply(self, content: str) -> str:
        """Apply the rule to the content and return the modified content."""
        pass
    
    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


#######################################
# FORMATTING RULES
#######################################

class RemoveBoldFromTitlesRule(Rule):
    """Rule to remove bold formatting from titles."""
    
    def __init__(self):
        super().__init__(
            "remove_bold_from_titles",
            "Removes bold formatting from titles (# **Title** -> # Title)"
        )
    
    def apply(self, content: str) -> str:
        """Remove bold formatting from titles."""
        return re.sub(r'(#\s+)\*\*(.*?)\*\*', r'\1\2', content)


#######################################
# TRANSITION RULES
#######################################

class DefaultTransitionRule(Rule):
    """Rule to ensure the default transition in the header is 'slide-down'."""
    
    def __init__(self):
        super().__init__(
            "default_transition",
            "Ensures the default transition in the header is 'slide-down'"
        )
    
    def apply(self, content: str) -> str:
        """Ensure the default transition in the header is 'slide-down'."""
        # Check if frontmatter header exists
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            
            # Ensure the default transition in the header is 'slide-down'
            if 'transition:' not in frontmatter:
                # Add transition: slide-down to the header
                new_frontmatter = frontmatter + "\ntransition: slide-down"
                content = content.replace(frontmatter, new_frontmatter)
            elif not re.search(r'transition:\s*slide-down', frontmatter):
                # Replace existing transition with slide-down
                content = re.sub(r'transition:\s*\S+', 'transition: slide-down', content, count=1)
        
        return content


class SectionTransitionRule(Rule):
    """Rule to add 'transition: slide-left' only for slides with layout 'section'."""
    
    def __init__(self):
        super().__init__(
            "section_transition",
            "Adds 'transition: slide-left' only for slides with layout 'section'"
        )
    
    def apply(self, content: str) -> str:
        """Add 'transition: slide-left' only for slides with layout 'section'."""
        # Find all section blocks without slide-left transition
        content = re.sub(
            r'(---\s*\nlayout:\s*section\s*\n)(?!transition:\s*slide-left)', 
            r'\1transition: slide-left\n', 
            content
        )
        
        # Find all blocks with layout: section and a transition other than slide-left
        content = re.sub(
            r'(---\s*\nlayout:\s*section\s*\n)transition:\s*(?!slide-left)\S+', 
            r'\1transition: slide-left', 
            content
        )
        
        return content


class CleanTransitionsRule(Rule):
    """Rule to clean up duplicate or misplaced transitions."""
    
    def __init__(self):
        super().__init__(
            "clean_transitions",
            "Cleans up duplicate or misplaced transitions"
        )
    
    def apply(self, content: str) -> str:
        """Clean up duplicate or misplaced transitions."""
        # Remove slide-down transitions added after normal slide separators
        content = re.sub(r'---\s*\ntransition:\s*slide-down\s*\n(?!layout:)', r'---\n\n', content)
        
        # Remove empty line at the beginning of the frontmatter
        content = re.sub(r'^---\s*\n\s*\n', r'---\n', content)
        
        # Fix frontmatter: ensure NO newlines between frontmatter end and first title
        # This is a direct approach using a more specific pattern
        content = re.sub(r'(---\s*\n)\s*\n+(#)', r'\1\2', content)
        
        # Ensure there's a line break after each internal slide separator UNLESS followed by a layout or transition
        content = re.sub(r'(\n---\s*\n)(?!\s*\n|layout:|transition:)', r'\1\n', content)
        
        return content


class EnsureSpaceBetweenTitleAndSubtitleRule(Rule):
    """Rule to ensure there is a blank line between a title and its subtitle."""
    
    def __init__(self):
        super().__init__(
            "ensure_space_between_title_subtitle",
            "Ensures there is a blank line between a title (#) and its subtitle (##)"
        )
    
    def apply(self, content: str) -> str:
        """Ensure there is a blank line between a title and its subtitle."""
        # Add a blank line between a title and its subtitle if not already present
        content = re.sub(r'(^#\s+.*$)\n(^##\s+.*$)', r'\1\n\n\2', content, flags=re.MULTILINE)
        
        return content


class AddSpacingAfterTitlesRule(Rule):
    """Rule to add a customizable HTML spacing tag after level 1 titles."""
    
    def __init__(self, tag: str = '<p class="py-2"/>'):
        self.tag = tag
        super().__init__(
            "add_spacing_after_titles",
            f"Adds an HTML tag {tag} after level 1 titles, except before tables"
        )
    
    def apply(self, content: str) -> str:
        """Add a customizable HTML spacing tag after level 1 titles, except before tables."""
        # Store the tag for use in regex patterns
        tag_escaped = re.escape(self.tag)
        # Split content into parts (frontmatter and document body)
        parts = re.split(r'---\s*\n.*?\n---\s*\n', content, maxsplit=1, flags=re.DOTALL)
        
        if len(parts) > 1:
            frontmatter = re.search(r'(---\s*\n.*?\n---\s*\n)', content, re.DOTALL).group(1)
            body = parts[1]
            
            # Temporarily replace HTML comments (presenter notes) with a marker
            presenter_notes = []
            
            def save_presenter_note(match):
                presenter_notes.append(match.group(0))
                return f"PRESENTER_NOTE_{len(presenter_notes) - 1}"
            
            # Save presenter notes
            body_without_notes = re.sub(r'<!--[\s\S]*?-->', save_presenter_note, body)
            
            # Split the body into individual slides
            slides = re.split(r'\n---\s*\n', body_without_notes)
            
            # Skip the first slide (main title) and process the others
            if len(slides) > 1:
                for i in range(1, len(slides)):
                    # Check if the slide contains more than just a title
                    if not re.match(r'^\s*#\s+[^\n]+\s*$', slides[i].strip()):
                        # Only look for level 1 titles (exactly one #) that are not immediately followed by:
                        # 1. A code block (```)
                        # 2. A table (|)
                        # 3. A subtitle (##)
                        # 4. The tag itself (already processed)
                        slides[i] = re.sub(
                            r'(^|\n)(#\s+[^\n]+\n)(?!\s*```|\s*\||\s*##|\s*' + tag_escaped + ')', 
                            r'\1\2\n' + self.tag + '\n', 
                            slides[i]
                        )
                
                # Rebuild the body while preserving appropriate line breaks
                body_without_notes = slides[0]
                for i in range(1, len(slides)):
                    # Check if the slide starts with a layout or transition
                    if re.match(r'^\s*(layout:|transition:)', slides[i].lstrip()):
                        body_without_notes += "\n---\n" + slides[i]  # No extra line break
                    else:
                        body_without_notes += "\n---\n\n" + slides[i]  # Add a line break
            
            # Avoid duplicates if the tag already exists
            duplicate_pattern = tag_escaped + r'\s*\n' + tag_escaped
            body_without_notes = re.sub(duplicate_pattern, self.tag, body_without_notes)
            
            # Restore presenter notes
            for i, note in enumerate(presenter_notes):
                body_without_notes = body_without_notes.replace(f"PRESENTER_NOTE_{i}", note)
            
            # Rebuild the content
            content = frontmatter + body_without_notes
        
        return content


#######################################
# RULE SETS
#######################################

class RuleSet:
    """A set of rules to apply."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.rules: List[Rule] = []
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)
    
    def apply(self, content: str) -> str:
        """Apply all enabled rules to the content."""
        for rule in self.rules:
            if rule.enabled:
                content = rule.apply(content)
        return content
    
    def __str__(self) -> str:
        return f"{self.name}: {self.description}\nRules:\n" + "\n".join(f"  - {rule}" for rule in self.rules)


#######################################
# MAIN LINTER
#######################################

class SlidevLinter:
    """Linter for Slidev presentations."""
    
    def __init__(self):
        self.rule_sets: Dict[str, RuleSet] = {}
        self.rules: Dict[str, Rule] = {}
        self._initialize_rules()
    
    def _initialize_rules(self) -> None:
        """Initialize available rules and rule sets."""
        # Individual rules
        self.rules["remove_bold_from_titles"] = RemoveBoldFromTitlesRule()
        self.rules["default_transition"] = DefaultTransitionRule()
        self.rules["section_transition"] = SectionTransitionRule()
        self.rules["clean_transitions"] = CleanTransitionsRule()
        self.rules["add_spacing_after_titles"] = AddSpacingAfterTitlesRule(tag='<p class="py-2"/>')
        self.rules["ensure_space_between_title_subtitle"] = EnsureSpaceBetweenTitleAndSubtitleRule()
        
        # Rule set: Basic formatting
        basic_formatting = RuleSet(
            "basic_formatting",
            "Basic formatting rules for Slidev presentations"
        )
        basic_formatting.add_rule(self.rules["remove_bold_from_titles"])
        basic_formatting.add_rule(self.rules["default_transition"])
        basic_formatting.add_rule(self.rules["section_transition"])
        basic_formatting.add_rule(self.rules["clean_transitions"])
        basic_formatting.add_rule(self.rules["ensure_space_between_title_subtitle"])
        
        # Rule set: Advanced formatting
        advanced_formatting = RuleSet(
            "advanced_formatting",
            "Advanced formatting rules for Slidev presentations"
        )
        advanced_formatting.add_rule(self.rules["remove_bold_from_titles"])
        advanced_formatting.add_rule(self.rules["default_transition"])
        advanced_formatting.add_rule(self.rules["section_transition"])
        advanced_formatting.add_rule(self.rules["clean_transitions"])
        advanced_formatting.add_rule(self.rules["add_spacing_after_titles"])
        advanced_formatting.add_rule(self.rules["ensure_space_between_title_subtitle"])
        
        # Add rule sets
        self.rule_sets["basic_formatting"] = basic_formatting
        self.rule_sets["advanced_formatting"] = advanced_formatting
    
    def get_available_rules(self) -> List[str]:
        """Return the list of available rules."""
        return list(self.rules.keys())
    
    def get_available_rule_sets(self) -> List[str]:
        """Return the list of available rule sets."""
        return list(self.rule_sets.keys())
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            return True
        return False
    
    def lint_file(self, file_path: str, rule_set_name: Optional[str] = None, rule_names: Optional[List[str]] = None) -> bool:
        """
        Lint a file with the specified rules.
        
        Args:
            file_path: Path to the file to lint
            rule_set_name: Name of the rule set to apply
            rule_names: List of individual rule names to apply
            
        Returns:
            True if modifications were made, False otherwise
        """
        print(f"Processing file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Save original content
        original_content = content
        
        if rule_set_name and rule_set_name in self.rule_sets:
            # Apply a rule set
            content = self.rule_sets[rule_set_name].apply(content)
        elif rule_names:
            # Apply individual rules
            for rule_name in rule_names:
                if rule_name in self.rules and self.rules[rule_name].enabled:
                    content = self.rules[rule_name].apply(content)
        
        # Check if modifications were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            print(f"✅ Applied modifications to {file_path}")
            return True
        else:
            print(f"ℹ️ No modifications needed for {file_path}")
            return False


#######################################
# COMMAND LINE INTERFACE
#######################################

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description='Linter for Slidev presentations.')
    parser.add_argument('--file', type=str, help='Process a specific file (e.g., 20-continuous-delivery.md)')
    parser.add_argument('--pattern', type=str, help='Process files matching a glob pattern (e.g., "2[0-9]-*.md" or "gitlab-*.md")')
    parser.add_argument('--all', action='store_true', help='Process all files')
    parser.add_argument('--rule-set', type=str, help='Rule set to apply')
    parser.add_argument('--rules', type=str, nargs='+', help='Individual rules to apply')
    parser.add_argument('--list-rules', action='store_true', help='List available rules')
    parser.add_argument('--list-rule-sets', action='store_true', help='List available rule sets')
    
    args = parser.parse_args()
    
    linter = SlidevLinter()
    
    if args.list_rules:
        print("Available rules:")
        for rule_name, rule in linter.rules.items():
            print(f"  - {rule_name}: {rule.description}")
        return
    
    if args.list_rule_sets:
        print("Available rule sets:")
        for rule_set_name, rule_set in linter.rule_sets.items():
            print(f"  - {rule_set_name}: {rule_set.description}")
            print("    Included rules:")
            for rule in rule_set.rules:
                print(f"      - {rule.name}: {rule.description}")
        return
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    slides_dir = os.path.join(base_dir, 'slides')
    
    files_to_process = []
    
    if args.file:
        # Process a specific file
        if os.path.isabs(args.file):
            file_path = args.file
        else:
            # If relative path, assume it's relative to the slides directory
            file_path = os.path.join(slides_dir, args.file)
        
        if os.path.isfile(file_path) and file_path.endswith('.md'):
            files_to_process = [file_path]
        else:
            # Check if it's a pattern like '20-*.md'
            if re.match(r'^\d+\-', args.file):
                pattern = args.file
                matched_files = glob.glob(os.path.join(slides_dir, pattern))
                if matched_files:
                    files_to_process = matched_files
                else:
                    print(f"Error: No files found matching pattern: {args.file}")
                    return
            else:
                print(f"Error: File not found or not a Markdown file: {file_path}")
                return
    elif args.pattern:
        # Process files matching a glob pattern
        pattern = args.pattern
        matched_files = glob.glob(os.path.join(slides_dir, pattern))
        if matched_files:
            files_to_process.extend(matched_files)
        else:
            print(f"Error: No files found matching pattern: {args.pattern}")
            return
    elif args.all:
        files_to_process = glob.glob(os.path.join(slides_dir, "[0-9][0-9]-*.md"))
    else:
        print("Error: Please specify --file, --pattern, or --all")
        return
    
    if not files_to_process:
        print("No files found matching the criteria.")
        return
    
    modified_count = 0
    for file_path in sorted(files_to_process):
        if linter.lint_file(file_path, args.rule_set, args.rules):
            modified_count += 1
    
    print(f"\nSummary: {modified_count}/{len(files_to_process)} files modified.")


if __name__ == "__main__":
    main()

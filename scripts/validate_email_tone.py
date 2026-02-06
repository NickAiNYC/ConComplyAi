#!/usr/bin/env python3
"""
Email Tone Validator for ConComplyAi Fixer Agent

Validates email templates and broker communication code against:
- Hemingway readability standards (Grade 10 max)
- Anti-pattern detection (robotic language, excessive formality)
- Construction industry tone requirements

Part of the Copilot Contract Enforcement suite.
"""
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict

try:
    import textstat
except ImportError:
    print("⚠️  textstat not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "textstat", "-q"])
    import textstat


class EmailToneValidator:
    """Validates email tone according to ConComplyAi construction industry standards"""
    
    # Anti-patterns from .github/copilot-instructions.md
    ANTI_PATTERNS = [
        ("I hope this email finds you well", "wastes time - get to the point"),
        ("I hope this finds you well", "wastes time - get to the point"),
        ("As per our previous conversation", "sounds robotic - be direct"),
        ("Per our previous conversation", "sounds robotic - be direct"),
        ("Please kindly", "too deferential for construction culture"),
        ("Kindly please", "too deferential for construction culture"),
        ("!!!", "unprofessional - avoid exclamation points"),
        ("Dear Sir or Madam", "too formal - use first names"),
        ("To Whom It May Concern", "too formal - use first names"),
        ("Regards,", "acceptable but 'Thanks,' is better for construction"),
        ("Best regards,", "too formal - use 'Thanks,'"),
        ("Yours sincerely,", "too formal - use 'Thanks,'"),
        ("Yours faithfully,", "too formal - use 'Thanks,'"),
    ]
    
    # Required elements for urgency
    URGENCY_KEYWORDS = [
        "deadline", "urgent", "by EOD", "by end of day", 
        "needed by", "required by", "due date"
    ]
    
    # Construction industry shorthand (good patterns)
    INDUSTRY_TERMS = {
        "GL": "General Liability",
        "AI": "Additional Insured", 
        "WOS": "Waiver of Subrogation",
        "COI": "Certificate of Insurance",
        "DDC": "Department of Design and Construction",
        "SCA": "School Construction Authority",
    }
    
    def __init__(self, template_dir: str):
        self.template_dir = Path(template_dir)
        self.violations: List[str] = []
        self.warnings: List[str] = []
        
    def validate_readability(self, content: str, filename: str) -> None:
        """Check Hemingway readability score (target: < 10)"""
        # Remove code-like content and template variables
        clean_content = re.sub(r'\{[^}]+\}', 'placeholder', content)
        clean_content = re.sub(r'https?://\S+', 'link', clean_content)
        
        if len(clean_content.strip()) < 50:
            # Too short to analyze meaningfully
            return
            
        try:
            score = textstat.flesch_kincaid_grade(clean_content)
            if score > 10:
                self.violations.append(
                    f"{filename}: Readability score {score:.1f} > 10 "
                    f"(target: high school sophomore level)"
                )
            elif score > 8:
                self.warnings.append(
                    f"{filename}: Readability score {score:.1f} is acceptable but aim for < 8"
                )
        except Exception as e:
            # Textstat can fail on very short or unusual text
            pass
    
    def check_anti_patterns(self, content: str, filename: str) -> None:
        """Detect anti-patterns from copilot instructions"""
        content_lower = content.lower()
        
        for phrase, reason in self.ANTI_PATTERNS:
            if phrase.lower() in content_lower:
                self.violations.append(
                    f"{filename}: Contains '{phrase}' - {reason}"
                )
    
    def check_urgency_markers(self, content: str, filename: str) -> None:
        """Verify emails include urgency/deadline information"""
        content_lower = content.lower()
        
        has_urgency = any(keyword in content_lower for keyword in self.URGENCY_KEYWORDS)
        
        # Check if this looks like a remediation/correction email
        is_remediation = any(term in content_lower for term in 
                            ["missing", "deficiency", "compliance", "required", "needed"])
        
        if is_remediation and not has_urgency:
            self.warnings.append(
                f"{filename}: Remediation email should include specific deadline "
                f"(e.g., 'by EOD Thursday', '48 hours')"
            )
    
    def check_sentence_length(self, content: str, filename: str) -> None:
        """Verify sentences are concise (< 20 words per copilot contract)"""
        # Split into sentences (basic splitting)
        sentences = re.split(r'[.!?]+', content)
        
        for i, sentence in enumerate(sentences, 1):
            # Clean up and count words
            clean_sentence = re.sub(r'\{[^}]+\}', 'X', sentence)
            clean_sentence = re.sub(r'https?://\S+', 'X', clean_sentence)
            words = clean_sentence.split()
            
            if len(words) > 20:
                self.warnings.append(
                    f"{filename}: Sentence {i} has {len(words)} words (max 20 recommended)"
                )
    
    def validate_template_file(self, filepath: Path) -> None:
        """Validate a single template file"""
        try:
            content = filepath.read_text(encoding='utf-8')
            filename = filepath.name
            
            self.validate_readability(content, filename)
            self.check_anti_patterns(content, filename)
            self.check_urgency_markers(content, filename)
            self.check_sentence_length(content, filename)
            
        except Exception as e:
            self.warnings.append(f"{filepath.name}: Error reading file - {e}")
    
    def validate_python_file(self, filepath: Path) -> None:
        """Validate email templates embedded in Python code (docstrings, strings)"""
        try:
            content = filepath.read_text(encoding='utf-8')
            filename = filepath.name
            
            # Extract multi-line strings and docstrings that might be email templates
            # Look for strings that contain email-like content
            if 'email' in content.lower() or 'subject:' in content.lower() or 'dear' in content.lower():
                # Extract docstrings (regular and f-strings)
                docstring_patterns = [
                    r'"""(.*?)"""',  # Regular docstrings
                    r'f"""(.*?)"""',  # F-string docstrings
                    r"'''(.*?)'''",   # Single quote docstrings
                    r"f'''(.*?)'''",  # F-string single quote
                ]
                
                all_strings = []
                for pattern in docstring_patterns:
                    all_strings.extend(re.findall(pattern, content, re.DOTALL))
                
                for i, string_content in enumerate(all_strings):
                    if any(marker in string_content.lower() for marker in 
                          ['subject:', 'dear', 'hello', 'hey', 'thanks,', 'regards,', 'best regards']):
                        # This looks like an email template
                        self.validate_readability(string_content, f"{filename} (string {i+1})")
                        self.check_anti_patterns(string_content, f"{filename} (string {i+1})")
                        self.check_sentence_length(string_content, f"{filename} (string {i+1})")
                        
        except Exception as e:
            pass  # Skip files that can't be read
    
    def validate_all(self) -> bool:
        """Validate all templates in directory"""
        template_path = Path(self.template_dir)
        
        # If it's a file, check just that file
        if template_path.is_file():
            if template_path.suffix == '.py':
                self.validate_python_file(template_path)
            else:
                self.validate_template_file(template_path)
            return len(self.violations) == 0
        
        # If directory doesn't exist, not a failure
        if not template_path.exists():
            print(f"ℹ️  Directory {template_path} does not exist")
            return True
        
        # Check for .txt, .md, .email template files
        template_files = list(template_path.glob("*.txt"))
        template_files.extend(template_path.glob("*.email"))
        template_files.extend(template_path.glob("*.md"))
        
        # Also check Python files for embedded templates
        py_files = list(template_path.glob("*liaison*.py"))
        py_files.extend(template_path.glob("*outreach*.py"))
        py_files.extend(template_path.glob("*fixer*.py"))
        py_files.extend(template_path.glob("*broker*.py"))
        
        if not template_files and not py_files:
            print(f"ℹ️  No email templates found in {template_path}")
            return True
        
        for template_file in template_files:
            self.validate_template_file(template_file)
        
        for py_file in py_files:
            self.validate_python_file(py_file)
        
        return len(self.violations) == 0
    
    def print_results(self) -> None:
        """Print validation results"""
        if self.violations:
            print("❌ Email Tone Violations:")
            for violation in self.violations:
                print(f"  - {violation}")
            print()
        
        if self.warnings:
            print("⚠️  Email Tone Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if not self.violations and not self.warnings:
            print("✅ All email templates pass tone validation")
        elif not self.violations:
            print("✅ No critical violations (warnings only)")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python validate_email_tone.py <template_directory_or_file>")
        print()
        print("Examples:")
        print("  python scripts/validate_email_tone.py core/agents/fixer/templates/")
        print("  python scripts/validate_email_tone.py core/agents/broker_liaison_agent.py")
        sys.exit(1)
    
    template_path = sys.argv[1]
    validator = EmailToneValidator(template_path)
    
    success = validator.validate_all()
    validator.print_results()
    
    if not success:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

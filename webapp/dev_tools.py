#!/usr/bin/env python3
"""
EAA Scanner Development Tools
Utilities for development, testing, and deployment
"""

import os
import sys
import subprocess
import gzip
import json
from pathlib import Path


class DevTools:
    """Development utilities for EAA Scanner"""
    
    def __init__(self):
        self.webapp_dir = Path(__file__).parent
        self.static_dir = self.webapp_dir / "static"
    
    def analyze_bundle_sizes(self):
        """Analyze bundle sizes of static assets"""
        print("📦 Bundle Size Analysis")
        print("=" * 50)
        
        assets = [
            self.static_dir / "css" / "main.css",
            self.static_dir / "js" / "scanner.js",
            self.static_dir / "js" / "history.js",
            self.static_dir / "js" / "sw.js",
        ]
        
        total_raw = 0
        total_gzipped = 0
        
        for asset in assets:
            if not asset.exists():
                print(f"❌ {asset.name}: File not found")
                continue
            
            raw_size = asset.stat().st_size
            
            # Calculate gzipped size
            with open(asset, 'rb') as f:
                gzipped_size = len(gzip.compress(f.read()))
            
            total_raw += raw_size
            total_gzipped += gzipped_size
            
            print(f"📄 {asset.name}")
            print(f"   Raw: {raw_size:,} bytes ({raw_size/1024:.1f} KB)")
            print(f"   Gzipped: {gzipped_size:,} bytes ({gzipped_size/1024:.1f} KB)")
            print(f"   Compression: {((raw_size - gzipped_size) / raw_size * 100):.1f}%")
            print()
        
        print(f"📊 TOTALS")
        print(f"   Raw: {total_raw:,} bytes ({total_raw/1024:.1f} KB)")
        print(f"   Gzipped: {total_gzipped:,} bytes ({total_gzipped/1024:.1f} KB)")
        print(f"   Overall Compression: {((total_raw - total_gzipped) / total_raw * 100):.1f}%")
    
    def validate_html(self):
        """Validate HTML templates"""
        print("🔍 HTML Validation")
        print("=" * 50)
        
        templates = [
            self.webapp_dir / "templates" / "index.html",
            self.webapp_dir / "templates" / "history.html",
        ]
        
        for template in templates:
            if not template.exists():
                print(f"❌ {template.name}: File not found")
                continue
            
            print(f"📄 Validating {template.name}...")
            
            # Basic HTML validation
            content = template.read_text(encoding='utf-8')
            
            checks = {
                "DOCTYPE": content.startswith("<!DOCTYPE html>"),
                "HTML lang": 'lang="it"' in content,
                "Meta charset": 'charset="utf-8"' in content,
                "Meta viewport": 'name="viewport"' in content,
                "Title": '<title>' in content,
                "Semantic HTML": any(tag in content for tag in ['<main', '<header', '<nav', '<section']),
                "ARIA attributes": 'aria-' in content,
                "Form labels": '<label' in content and 'for=' in content,
            }
            
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check}")
            
            print()
    
    def check_accessibility(self):
        """Check accessibility features in templates"""
        print("♿ Accessibility Check")
        print("=" * 50)
        
        templates = [
            self.webapp_dir / "templates" / "index.html",
            self.webapp_dir / "templates" / "history.html",
        ]
        
        for template in templates:
            if not template.exists():
                continue
            
            content = template.read_text(encoding='utf-8')
            
            print(f"📄 {template.name}")
            
            accessibility_checks = {
                "Language attribute": 'lang="' in content,
                "Skip links": 'skip' in content.lower(),
                "ARIA labels": 'aria-label=' in content,
                "ARIA describedby": 'aria-describedby=' in content,
                "Form labels": '<label for=' in content,
                "Button text": '<button' in content and not 'aria-label' in content,
                "Image alt text": 'alt=' in content if '<img' in content else True,
                "Focus management": 'focus' in content.lower(),
                "Color contrast": '--text-' in content,  # Check if CSS variables are used
            }
            
            for check, passed in accessibility_checks.items():
                status = "✅" if passed else "⚠️"
                print(f"   {status} {check}")
            
            print()
    
    def optimize_css(self):
        """Optimize CSS file"""
        print("🎨 CSS Optimization")
        print("=" * 50)
        
        css_file = self.static_dir / "css" / "main.css"
        
        if not css_file.exists():
            print("❌ CSS file not found")
            return
        
        content = css_file.read_text(encoding='utf-8')
        
        # Basic optimization stats
        original_size = len(content)
        lines = content.count('\n')
        comments = content.count('/*')
        
        print(f"📄 Analyzing {css_file.name}")
        print(f"   Size: {original_size:,} bytes ({original_size/1024:.1f} KB)")
        print(f"   Lines: {lines:,}")
        print(f"   Comments: {comments}")
        
        # Check for common CSS patterns
        patterns = {
            "CSS Variables": '--' in content,
            "Media Queries": '@media' in content,
            "Grid Layout": 'grid-template' in content,
            "Flexbox": 'flex' in content,
            "Animations": '@keyframes' in content,
            "Modern Properties": any(prop in content for prop in ['clamp(', 'min(', 'max(']),
        }
        
        print(f"\n🔍 CSS Features:")
        for pattern, found in patterns.items():
            status = "✅" if found else "❌"
            print(f"   {status} {pattern}")
    
    def generate_manifest(self):
        """Generate PWA manifest file"""
        print("📱 Generating PWA Manifest")
        print("=" * 50)
        
        manifest = {
            "name": "EAA Scanner - Accessibility Tool",
            "short_name": "EAA Scanner",
            "description": "Automated accessibility scanning for WCAG and EAA compliance",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#3b82f6",
            "orientation": "portrait-primary",
            "scope": "/",
            "lang": "it",
            "icons": [
                {
                    "src": "/static/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ],
            "categories": ["productivity", "utilities", "developer"],
            "screenshots": [
                {
                    "src": "/static/screenshots/desktop.png",
                    "sizes": "1280x720",
                    "type": "image/png",
                    "form_factor": "wide"
                },
                {
                    "src": "/static/screenshots/mobile.png",
                    "sizes": "390x844",
                    "type": "image/png",
                    "form_factor": "narrow"
                }
            ]
        }
        
        manifest_path = self.static_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Manifest generated: {manifest_path}")
        print(f"   Add to HTML: <link rel=\"manifest\" href=\"/static/manifest.json\">")
    
    def check_performance(self):
        """Check performance best practices"""
        print("⚡ Performance Check")
        print("=" * 50)
        
        # Check for common performance issues
        js_files = list((self.static_dir / "js").glob("*.js"))
        css_files = list((self.static_dir / "css").glob("*.css"))
        
        print("📊 Asset Analysis:")
        
        for js_file in js_files:
            size = js_file.stat().st_size
            content = js_file.read_text(encoding='utf-8')
            
            print(f"   📄 {js_file.name}: {size:,} bytes")
            
            # Check for performance issues
            issues = []
            if 'console.log' in content:
                issues.append("Console logs found")
            if size > 100 * 1024:  # > 100KB
                issues.append("Large file size")
            if 'document.write' in content:
                issues.append("Blocking document.write")
            
            if issues:
                for issue in issues:
                    print(f"      ⚠️  {issue}")
            else:
                print(f"      ✅ No issues found")
        
        for css_file in css_files:
            size = css_file.stat().st_size
            content = css_file.read_text(encoding='utf-8')
            
            print(f"   🎨 {css_file.name}: {size:,} bytes")
            
            # Check for CSS performance issues
            issues = []
            if size > 50 * 1024:  # > 50KB
                issues.append("Large CSS file")
            if content.count('@import') > 0:
                issues.append("CSS imports found (blocking)")
            
            if issues:
                for issue in issues:
                    print(f"      ⚠️  {issue}")
            else:
                print(f"      ✅ No issues found")
    
    def run_all_checks(self):
        """Run all development checks"""
        checks = [
            self.analyze_bundle_sizes,
            self.validate_html,
            self.check_accessibility,
            self.optimize_css,
            self.check_performance,
        ]
        
        for check in checks:
            try:
                check()
                print()
            except Exception as e:
                print(f"❌ Error in {check.__name__}: {e}")
                print()


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("🛠 EAA Scanner Development Tools")
        print("Usage: python dev_tools.py <command>")
        print("\nCommands:")
        print("  bundle-size    - Analyze bundle sizes")
        print("  validate-html  - Validate HTML templates")
        print("  check-a11y     - Check accessibility features")
        print("  optimize-css   - Analyze CSS optimization")
        print("  generate-manifest - Generate PWA manifest")
        print("  check-perf     - Check performance")
        print("  all            - Run all checks")
        return
    
    command = sys.argv[1]
    tools = DevTools()
    
    commands = {
        "bundle-size": tools.analyze_bundle_sizes,
        "validate-html": tools.validate_html,
        "check-a11y": tools.check_accessibility,
        "optimize-css": tools.optimize_css,
        "generate-manifest": tools.generate_manifest,
        "check-perf": tools.check_performance,
        "all": tools.run_all_checks,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()
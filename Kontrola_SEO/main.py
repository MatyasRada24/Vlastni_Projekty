"""Desktop entry point; optional command-line audit also supports packaged checks."""
import argparse
import sys


def run():
    parser = argparse.ArgumentParser(description='Kontrola SEO pro Windows')
    parser.add_argument('--audit-url', help='Provést URL audit bez otevření okna')
    parser.add_argument('--render-js', action='store_true', help='Vykreslit JavaScript')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--output', help='Cílový HTML nebo JSON report pro audit bez okna')
    args = parser.parse_args()
    if args.audit_url:
        if not args.output or not 1 <= args.limit <= 1000:
            parser.error('Pro --audit-url je nutné --output a limit 1–1000.')
        from seo_checker.engine import audit_url
        from seo_checker.export import save_report
        report = audit_url(args.audit_url, limit=args.limit, rendering=args.render_js)
        save_report(report, args.output)
    else:
        from seo_checker.app import main
        main()

if __name__ == "__main__":
    run()

"""Console-subsystem worker; QProcess supplies pipes and hides its console."""

from molrecognizer.render_worker import main

if __name__ == "__main__":
    raise SystemExit(main())

"""
_version.py: Version and release channel

CI rewrites this file from the git tag before packaging:
  v0.1.0            -> CHANNEL = "Stable"
  v0.1.0-beta.1     -> CHANNEL = "Pre-release"   (also -alpha.N, -rc.N)
  untagged commits  -> CHANNEL = "Nightly"
"""

VERSION = "0.1.0-beta.5"
CHANNEL = "Development"
COMMIT  = ""

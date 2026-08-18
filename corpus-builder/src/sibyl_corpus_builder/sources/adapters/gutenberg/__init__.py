"""Project Gutenberg acquisition and canonicalization adapter.

It locates a preferred plain-text artifact when needed and removes only the
recognized Gutenberg transport wrapper before generic source caching and
preparation. Network access is explicit. Registry approval, rights policy,
artifact persistence, and later corpus building remain outside this adapter."""

"""Probe tool for the 'Inside the Block' Superteam Earn bounty.

Measures how production Solana validators order transactions inside the
blocks they lead, using only self-sent probe transactions as evidence.
Dry-run by default; live sending is behind an explicit flag, an env-supplied
keypair, a balance check, and a code-enforced cumulative fee cap.
"""

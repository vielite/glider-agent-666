# Smart Contract Vulnerability Audit - SolvBTC

**Date:** 2026-03-20
**Scope:** `programs/solvbtc/src`
**Files:** 18
**Framework:** anchor

---

## Executive Snapshot

- Findings: total=2 (Critical=0, High=0, Medium=2, Low=0, Info=0)
- Confidence: high-confidence=1, needs-manual-review=1
- Highest-risk theme: signer-capable PDAs are reused without always proving the backing Vault state exists
- Immediate action: harden the minter-manager vault input and enforce fee invariants during currency onboarding

---

### [MEDIUM] Deposit fee can be stored above `MAX_FEE` during currency onboarding

**ID:** `CAND-001`
**File:** `programs/solvbtc/src/state/vault.rs` L103
**Severity:** `Medium`
**Confidence:** `0.93` (`high-confidence`)
**Description:** `Vault::add_currency` accepts any `deposit_fee` and writes it into state without the `MAX_FEE` bound enforced by `initialize`, `set_deposit_fee`, and `set_withdraw_fee`. Once such a currency is onboarded, future deposits into that currency can revert because `calculate_fee` subtracts a fee that may exceed the minted amount.

**Code:**
```rust
pub fn add_currency(&mut self, mint: Pubkey, deposit_fee: u16) -> Result<()> {
    if let Some(empty_index) = self.deposit_currencies.iter().position(
        |&token| token.mint.eq(&Pubkey::default()),
    ) {
        self.deposit_currencies[empty_index] = WhitelistedToken { mint, deposit_fee };
        self.update()
    } else {
        Err(SolvError::CurrencyArrayFull.into())
    }
}

pub fn calculate_fee(amount: u64, fee: u16) -> Result<(u64, u64)> {
    let fee: u64 = u128::from(amount)
        .checked_mul(fee as u128)
        .ok_or(ProgramError::ArithmeticOverflow)?
        .checked_div(MAX_FEE.into())
        .ok_or(ProgramError::ArithmeticOverflow)?
        .try_into()
        .map_err(|_| ProgramError::ArithmeticOverflow)?;
    let amount = amount.checked_sub(fee).ok_or(ProgramError::ArithmeticOverflow)?;
    Ok((amount, fee))
}
```

**Recommendation:** Apply the same `require_gte!(MAX_FEE, deposit_fee, SolvError::InvalidFeeRatio)` guard inside `add_currency`. It is also worth adding a regression test that attempts to onboard a currency with `deposit_fee > 10_000`.

---

### [MEDIUM] Minter manager accepts a synthetic vault PDA with no initialized `Vault` state

**ID:** `CAND-002`
**File:** `programs/solvbtc/src/contexts/minter_manager_initialize.rs` L13
**Severity:** `High -> Medium`
**Confidence:** `0.68` (`needs-manual-review`)
**Description:** The minter-manager flow only checks that `vault` has the PDA shape derived from `[b"vault", mint]`; it never proves that the address is an initialized `Vault` account owned by this program. The mint path then reuses that same unchecked PDA as a signer, which weakens the assumption that every mint operation is anchored to real vault state.

**Code:**
```rust
#[account(
    seeds = [b"vault", mint.key().as_ref()],
    bump
)]
pub vault: AccountInfo<'info>,

#[account(
    seeds = [b"vault", mint.key().as_ref()],
    bump
)]
pub vault: AccountInfo<'info>,

let signer_seeds: [&[&[u8]];1] =
    [&[b"vault".as_ref(), self.mint.to_account_info().key.as_ref(), &pda_bump]];
```

**Recommendation:** Require `vault` to deserialize as `Account<'info, Vault>` in both `MinterManagerInitialize` and `MinterManagerMint`, or manually verify owner, discriminator, and stored mint before using it as a signer. That preserves the invariant that mint authorization only flows through initialized vault state.

**Notes:** Downgraded from High because local evidence shows two strong preconditions: a hardcoded `ADMIN_WHITELIST` bootstrap authority must create the manager first, and the external token mint must already trust the PDA as part of its multisig authority.

---

## Severity Summary

| Severity      | Count |
|---------------|-------|
| Critical      | 0     |
| High          | 0     |
| Medium        | 2     |
| Low           | 0     |
| Informational | 0     |

## Checklist Summary

| Status  | Count |
|---------|-------|
| PASS    | 65    |
| FAIL    | 2     |
| UNKNOWN | 0     |

## Triage

| Decision               | Count |
|------------------------|-------|
| valid                  | 1     |
| valid_downgraded       | 1     |
| false_positive_dropped | 1     |

## Prioritized Remediation

1. In the next 72 hours, harden `MinterManagerInitialize` and `MinterManagerMint` so they only accept initialized `Vault` accounts before any PDA signer use.
2. In the next 7 days, enforce `deposit_fee <= MAX_FEE` inside `add_currency` and add regression coverage for invalid onboarding values.
3. In the next 30 days, document and test the asset-invariant assumptions for whitelisted deposit currencies so future onboarding cannot silently violate pricing expectations.

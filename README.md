# 🛡️ Data Shield — User Guide

**Data Shield** is a Speckle Automate function that helps you keep your model data clean, safe, and share-ready. Whether you're sending models to clients, collaborators, or just tidying up before archiving — Data Shield’s got your back.

---

## ✨ What Data Shield Does

Data Shield scans your Speckle model for parameters you’d rather not share and takes care of them for you. It creates a fresh, sanitized version of your model while keeping the original intact.

### Why you’ll love it:
- **Privacy Protection** — Say goodbye to accidentally sharing sensitive data.
- **Data Compliance** — Stay on the right side of data protection policies.
- **Confident Collaboration** — Share models without oversharing.

---

## Sanitization Modes

We know one size doesn’t fit all, so Data Shield offers three modes to suit your style:

### Prefix Matching
> **Best for:** Simple, predictable naming conventions.

Remove parameters that start with a specific prefix.
> Example: Want to remove everything starting with `secret_`? Just set that prefix and Data Shield does the rest.

**Setup**:
- Add your prefix (like `internal_`, `private_`, or `secret_`)
- Toggle strict mode for case sensitivity (on or off — your call)

---

### Pattern Matching
> **Best for:** Wildcards, regex fans, and complex patterns.

Get fancy and use `*`, `?`, or full regular expressions.

**Examples**:
- `client_*` matches anything that starts with `client_`
- `?_internal` matches `a_internal`, `b_internal`
- `/^(secret|private)_.*$/i` matches parameters starting with `secret_` or `private_`, ignoring case

---

### Anonymization
> **Best for:** Keeping the structure, hiding the details.

Automatically detect email addresses inside parameter values and anonymize them.
> Example: `john.doe@example.com` becomes `j***@example.com`

No setup needed. Just select and go.

---

## How to Use Data Shield

1. **Set up your automation:**
    - In your Speckle project, head to **Automations**
    - Click **Add Automation** and choose **Data Shield**
    - Set your trigger (like “on new commit”)

2. **Configure your mode:**
    - Choose Prefix, Pattern, or Anonymization
    - Add your prefix or pattern if needed
    - Toggle strict mode if you want case sensitivity

3. **Run it:**
    - It’ll run automatically when triggered — or you can manually run on specific commits

4. **Check results:**
    - Sanitized models show up under the `processed/` branch
    - You’ll get a run report showing what got cleaned
    - Highlighted changes can be seen directly in the viewer

::: 💡 Tips & Tricks

- **Test first!** — Run it on a small test model before going full production.
- **Start simple.** Use prefix matching for clear conventions, pattern matching for complexity, or anonymization for safe sharing.
- **Regex pro tip:**
    - Wrap your regex in `/`
    - Add `i` for case-insensitive matching
    - Use `^` (start) and `$` (end) for tighter control
:::


## 📚 Example Workflows

### → Prepping for external sharing
- Use pattern matching with `/^(internal|private|confidential)_.*$/i`
- Run before sending out models
- Share confidently!

### → Anonymizing client data
- Select Anonymization mode
- Run on any models with contact details
- Use sanitized versions for demos, public decks, or sales pitches

### → Stripping out project-specific baggage
- Prefix matching with something like `projectX_`
- Clean your models before turning them into templates

---

## 🛠️ Troubleshooting

- **Not matching anything?** Double-check your pattern or prefix.
- **Case mismatch?** Try turning off strict mode.
- **Only partly sanitized?** Some complex models might need multiple passes.
- **Errors?** Check run logs in the automation report for clues.

---

## 🤔 Still stuck?

No worries — we’ve got your back.  
👉 Post your questions in the [Speckle Community Forum](https://speckle.community) and someone from the team (or one of our awesome community members) will help you out!  

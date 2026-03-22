## Frontend Communication Patterns

- One user action = one API call. Combine related sequential calls into single endpoints.
- Use response data directly - don't discard it and refetch the same information.
- Atomic state updates: update all related state from a single response to prevent flickering.
- API client methods named after user actions, not backend structure.

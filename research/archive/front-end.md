### Next.js

_Frontend-Backend Communication Optimisation_

**Reduce API Calls**

* One user action should ideally equal one API call

* Combine related sequential calls into single endpoints where backend supports it

* Avoid fire-and-forget calls followed by refetch calls

**Use Response Data Directly**

* Don't fetch data separately if it's already returned in a response

* Design API responses to include everything needed for UI update

* Avoid discarding response data and refetching the same information

**Atomic State Updates**

* Update all related state from a single response

* Ensures UI consistency and prevents intermediate states

* Reduces flickering and multiple loading spinners

**API Client Design**

* Design API methods around user actions, not backend structure

* Method names should reflect what the user is doing, not implementation details

* Return types should match what the UI needs to render

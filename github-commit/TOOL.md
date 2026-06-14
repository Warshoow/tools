GitHub commit viewer — a single React component listing your commits across all repos in a date range.

`main.jsx` is one self-contained `export default function App()` (React hooks + inline
styles, no extra deps). Enter a GitHub username + a Personal Access Token and it fetches
your commits across every repo you own/collaborate on within a date window (default: last
14 days), with light/dark theming and a per-repo breakdown. The token stays in the browser
and is only sent to `api.github.com`.

## Run it locally

```bash
grab add github-commit
grab exec github-commit          # serves it via a throwaway Vite + React harness
```

First run scaffolds a `.preview/` (Vite + React) next to the component and installs deps;
subsequent runs reuse it and re-sync `main.jsx`. Requires Node.js >= 20. Open the URL Vite
prints (default http://localhost:5173).

```bash
grab exec github-commit build    # production build into .preview/dist
```

## Or drop it into a project

It's a plain default-export component — paste/import it into any React app (Vite, Next,
a claude.ai artifact, etc.):

```jsx
import GithubCommits from "./main.jsx";
```

## Notes

- Create a token at https://github.com/settings/tokens with `repo` read scope.
- `.preview/` lives under `.grab/tools/`, so it stays out of your project's git.

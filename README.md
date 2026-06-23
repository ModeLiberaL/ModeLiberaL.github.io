# ModeLiberaL.github.io

This is a static personal homepage that can be published directly with GitHub Pages.

## Files

- Home page: `index.html`
- Styles: `styles.css`
- Profile image: `assets/profile.jpg`

Replace the remaining introduction and project text in `index.html` as needed.

## Publish

1. Add the SSH public key to GitHub: `Settings -> SSH and GPG keys -> New SSH key`
2. Create a repository named `ModeLiberaL.github.io`
3. Set the remote repository:

   ```powershell
   git remote add origin git@github.com:ModeLiberaL/ModeLiberaL.github.io.git
   ```

4. Commit and push:

   ```powershell
   git add .
   git commit -m "Create personal homepage"
   git branch -M main
   git push -u origin main
   ```

After publishing, visit `https://ModeLiberaL.github.io`.

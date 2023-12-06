## Running Locally

After cloning the repo, put your API key in `.env`.

Then, run the following in the command line and your application will be available at `http://localhost:3000`

```bash
npm i -g vercel
vercel dev
```

To use the API route, go to the link below in your browser or run a curl command in your terminal to get a sample result. Feel free to replace the dub.sh link with a link to any image.

```bash
curl http://localhost:3000/generate?imageUrl=https://dub.sh/confpic
```

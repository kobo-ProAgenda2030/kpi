 #!/bin/bash
npm i &&
npm run copy-fonts &&
npm run build &&
rm -r /Users/sam/projects/groots/kobo-docker/.vols/static/kpi/compiled &&
mv /Users/sam/projects/groots/kpi/jsapp/compiled /Users/sam/projects/groots/kobo-docker/.vols/static/kpi
# udacity-multi-user-blog

A bare bones multi-user blog created as an exercise in web development.

This blog is built for deployment on Google's app engine. To develop or deploy this project, install the [Google Cloud SDK](https://cloud.google.com/sdk/).

After installing the SDK, the following command can be used to start a development server from the project directory.

    `dev_appserver ./`

To deploy to Google App Engine, use the following command, substituting in the project id and version as appropriate. It may be necessary to invoke this with a complete path to `appcfg.py`, since it seems that the SDK installation doesn't always correctly set all PATH variables.

    `appcfg.py -A [YOUR_PROJECT_ID] -V v1 update ./`

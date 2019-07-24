#!/usr/bin/env python
import argparse,collections,json,shlex,subprocess,sys,urllib,yaml

# Ordered YAML loading
def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, dict_constructor)

# Command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", dest="dryrun", action="store_const", const=True, default=False, help="Do not commit changes to the repository")
parser.add_argument("--push", dest="push", action="store_const", const=True, default=False, help="Execute git push after commit")
parser.add_argument("repository", nargs="+", help="Path to the git repositories to process")
args = parser.parse_args()

# retrieve latest atlassian version via REST api
def get_latest_version(application):
    data = urllib.urlopen("https://marketplace.atlassian.com/rest/1.0/applications/" + application + "/latest").read()
    output = json.loads(data)
    return output["version"]

def run_cmd(cmd, repo):
    p = subprocess.Popen(shlex.split(cmd), cwd=repo)
    p.communicate()
    if p.returncode != 0:
        sys.exit(1)

# main logic
for repo in args.repository:
    name = ""
    with open("{}/FORMULA".format(repo), 'r') as stream:
        name = yaml.load(stream, Loader=yaml.SafeLoader)["name"]
    print "{}:".format(name)
    run_cmd("git pull --quiet", repo)
    defaults_yaml = "{}/{}/defaults.yaml".format(repo, name)
    with open(defaults_yaml, 'r') as stream:
        defaults = yaml.load(stream, Loader=yaml.SafeLoader)
        current = defaults[name]["version"]
        latest = get_latest_version(name[10:])
        print "  Current version: {}".format(current)
        print "  Latest  version: {}".format(latest)
        if not args.dryrun and current != latest:
            # update defaults.yaml
            defaults[name]["version"] = bytes(latest)
            with open(defaults_yaml, 'w') as outfile:
                outfile.write(yaml.dump(defaults, default_flow_style=False))

            # git commit
            run_cmd("git add {}/defaults.yaml".format(name), repo)
            run_cmd("git commit -m 'update to {}'".format(latest), repo)
            if args.push:
                run_cmd("git push", repo)


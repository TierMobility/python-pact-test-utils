import requests
import argparse
import pathlib
import json


class PublishingFailedException(Exception):
    pass


class PactBrokerInterface:
    """ Interface to a pact-broker instance

    Allows publishing pact test JSON files to pact-broker instance

    Attributes
    ----------
    url : str
        pact-broker URL
    user : str
        pact-broker username
    password : str
        pact-broker password
    auth : tuple
        (user, password) for request's HTTPBasicAuth
    glob : str
        glob pattern to match pact files
    sep : str
        separator for extracting Consumer/Producer name from filename
    """

    def __init__(self, url, user, password, glob="*-pact.json", sep="-"):
        self.url = url.strip("/")
        self.user = user
        self.password = password
        self.auth = (self.user, self.password)
        self.glob = glob
        self.sep = sep
        self.headers = {'Content-Type': 'application/json'}

    def find_pacts(self, pact_path=".", version="1.0.0"):
        """ Find local pact files and prepare publication

        Parameters
        ----------
        pact_path : str
            Filepath or directory containing pact JSON file
        version : str
            (Consumer) application version

        Returns
        -------
        dict
            Keys:   Pact file name
            Values: URL & body for publication to pact-broker
        """

        publication = {}
        path = pathlib.Path(pact_path)
        if not path.exists():
            raise ValueError(f"Unable to find {pact_path}. No such file or directory.")
        if path.is_dir():
            pathlist = path.glob(f"**/{self.glob}")
            for pact in pathlist:
                consumer, provider, _ = pact.stem.split(self.sep)
                publish_url = f"{self.url}/pacts/provider/{provider}/consumer/{consumer}/version/{version}"
                with open(pact, "r") as stream:
                    data = json.load(stream)
                publication[pact.name] = {"url": publish_url, "data": data}
        elif path.is_file() and path.suffix.lower() == ".json":
            consumer, provider, _ = path.stem.split(self.sep)
            publish_url = f"{self.url}/pacts/provider/{provider}/consumer/{consumer}/version/{version}"
            with open(path, "r") as stream:
                data = json.load(stream)
            publication[path.name] = {"url": publish_url, "data": data}
        return publication

    def publish(self, publication):
        """ Publish pact to pact-broker instance

        Parameters
        ----------
        publication : dict
            Keys:   Pact file name
            Values: URL & body for publication to pact-broker
            Returned by PactBrokerInterface.find_pacts(...)
        """

        for name in publication:
            response = requests.put(publication[name]["url"], json=publication[name]["data"], auth=self.auth)
            response.raise_for_status()
            if response.status_code == 201:
                print(f"Published new pact {name} to {self.url}")
            elif response.status_code == 200:
                print(f"Published pact update {name} to {self.url}")

    def tag_version(self, participant, version, tag):
        tag_url = f'{self.url}/pacticipants/{participant}/versions/{version}/tags/{tag}'
        response = requests.put(
            tag_url, auth=self.auth, headers={'Content-Length': '0', 'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        if 200 <= response.status_code < 300:
            print(f'Tagged {participant} version {version} to with {tag}')

    def get_consumers(self, publication):
        consumers = set()
        for name in publication:
            consumers.add(name.split(self.sep, 1)[0])
        return list(consumers)


def main():
    parser = argparse.ArgumentParser(description="Publish pact test JSONs to pact-broker")
    parser.add_argument("url", help="URL of the pact-broker", type=str)
    parser.add_argument("username", help="pact-broker username", type=str)
    parser.add_argument("password", help="pact-broker password", type=str)
    parser.add_argument(
        "path", help="Location of pact JSON file(s) [file|dir]", nargs="?", type=str, default="."
    )
    parser.add_argument(
        "-v", "--version", help="Application version", type=str, default="1.0.0", dest="version"
    )
    parser.add_argument(
        "-g",
        "--glob",
        help="Glob pattern for matching pact files",
        default="*-pact.json",
        type=str,
        dest="glob",
    )
    parser.add_argument(
        "-s",
        "--separator",
        help="Separator for extracting Consumer/Producer name from pactfile",
        default="-",
        type=str,
        dest="sep",
    )
    parser.add_argument(
        "-t", "--tag", help="Consumer tag for the version", default="latest", type=str, dest="tag"
    )
    args = parser.parse_args()

    broker = PactBrokerInterface(args.url, args.username, args.password, args.glob, args.sep)

    publication = broker.find_pacts(args.path, args.version)
    broker.publish(publication)

    for consumer in broker.get_consumers(publication):
        broker.tag_version(consumer, args.version, args.tag)



if __name__ == "__main__":
    main()
    
# coding: utf-8

""" Visualize network components. """

from __future__ import division, print_function

__author__ = "Andy Casey <acasey@mso.anu.edu.au>"

# Standard libary
import itertools
import json
import os

# Module specific
from search import search as ads_search
from utils import unique_preserved_list

__all__ = ['nodes', 'export', 'coauthors']


def coauthors(name, depth, author_repr=None, rows=5):
    """Build a network of co-authors based on the name provided,
    to a level depth as provided.

    Inputs
    ------
    name : str
        The author name to focus on.

    depth : int
        The number of depth levels to progress from `name`.
    """

    try:
        depth = int(depth)
    except TypeError:
        raise TypeError("depth must be an integer-like type")

    if depth < 1:
        raise ValueError("depth must be a positive integer")

    if author_repr is None:
        author_repr = lambda x: x

    all_articles = []
    level_authors = [name]
    for i in xrange(depth):

        print((i, level_authors))
        next_level_authors = []
        for j, author in enumerate(level_authors):

            # If this is a "Collaboration" or "Team",
            # we should ignore it and just deal with
            # *real* people.

            if "collaboration" in author.lower() \
            or " team" in author.lower():
                continue

            # Get 5 top articles by this author
            articles = ads_search(u'"{author}"'.format(author=author),
                fl="author,citation_count", filter="property:refereed", rows=rows if [i, j] != [0, 0] else 5,
                order="desc", sort="citations")

            # Add these articles to the list
            all_articles.extend(articles)

            # Put these authors into the next level
            next_level_authors.extend(sum([article.author for article in articles], []))

        level_authors = []
        level_authors.extend(next_level_authors)


    # Initialise a group with the name input
    links = []
    groups = [0]
    values = []
    nodes = [author_repr(name)]

    # Remove article double-ups?

    # Go through all articles
    for group_number, article in enumerate(all_articles, start=1):

        print(article.author)
        # Make sure each co-author has a node
        # Limit each paper to 10 authors
        for co_author in article.author:

            co_author = author_repr(co_author)
            if co_author not in nodes:

                # Create the node for this author
                groups.append(group_number)
                nodes.append(author_repr(co_author))

        # Links should be drawn between all these article.author's,
        # since they all published together.
        for (author_one, author_two) in itertools.combinations(article.author, 2):
            print((author_one, author_two))
            if name in (author_one, author_two):
                print("!!!!!!")
            if author_repr(author_one) == author_repr(author_two):
                print("skipped")
                continue

            source = nodes.index(author_repr(author_one))
            target = nodes.index(author_repr(author_two))

            link = (source, target)
            knil = (target, source)
            if link not in links and knil not in links:
                print("adding link")
                links.append(link)
                values.append(1)

            else:
                print(" ")
                try:
                    index = links.index(link)
                except:
                    index = links.index(knil)

                values[index] += 1

    # Build formatted nodes and links
    formatted_nodes = []
    for author, group in zip(nodes, groups):
        formatted_nodes.append({"name": author, "group": group})

    formatted_links = []
    for (source, target), value in zip(links, values):
        formatted_links.append({
            "source": source,
            "target": target,
            "value": value
            })

    output = {
        "nodes": formatted_nodes,
        "links": formatted_links
    }

    return output


def nodes(articles, attribute, map_func=None):
    """Returns a dictionary of articles linked to each other, as
    defined by the attribute (either references or citations).

    Inputs
    ------
    articles : list of `Article` objects
        The articles with network information.

    attribute : citations or references
        The attribute build the nodes from.

    map_func : func, optional
        A callable function that takes a single `Article` object.
        If not None, this callable will be applied to every `Article`
        in the network.

    Examples
    --------
    The psuedocode below will return a paper, build a citation tree from
    it of depth 2, then return a network of how first authors cite `articles`.

        paper = ads.search("etc")
        paper.build_citation_tree(2)
        network = ads.network.nodes(paper, "citations", lambda article: article.author[0])

    """

    if not attribute in ("references", "citations"):
        raise ValueError("attribute must be either 'references' or 'citations'")

    if map_func is None:
        map_func = lambda _: _

    def recursive_walk(articles):

        branch = []
        for article in articles:
            if hasattr(article, "_{attribute}".format(attribute=attribute)):
                branch.append({
                    map_func(article): recursive_walk(getattr(article, "_{attribute}".format(attribute=attribute)))
                    })

            else:
                branch.append(map_func(article))

        return branch

    if not isinstance(articles, (list, tuple)):
        articles = [articles]

    return recursive_walk(articles)


def export(articles, attribute, output_filename, structure="nested", article_repr=None,
    new_branch_repr=None, end_branch_repr=None, clobber=False, **kwargs):
    """Export the article network attributes (e.g. either references or citations) for the
    given articles.

    Inputs
    ------
    articles : `Article` or list of `Articles`
        The articles to build the network with.

    attribute : "citations" or "references"
        The attribute to build the network with.

    output_filename : str
        The output filename to save the network to.

    structure : "nested" or "flat"
        Whether to return a nested or flat structure.

    article_repr : callable, optional
        A callable function to represent the article for each node.

    new_branch_repr : callable, optional
        A callable function to represent each sub branch.

    end_branch_repr : callable, optional
        A callable function to represent the end of a branch.

    clobber : bool
        Whether to clobber `output_filename` if it already exists.
    """

    if attribute not in ("citations", "references"):
        raise ValueError("attribute must be either 'citations' or 'references'")

    if structure not in ("nested", "flat"):
        raise ValueError("structure must be either 'flat' or 'nested'")

    if os.path.exists(output_filename) and not clobber:
        raise IOError("output filename ({filename}) already exists, and we've "
            "been told not to clobber it".format(filename=output_filename))

    if article_repr is None:
        article_repr = lambda x: x

    if new_branch_repr is None:
        new_branch_repr = lambda x, y: {x: y}

    if end_branch_repr is None:
        end_branch_repr = lambda x: x

    flat_data = []

    def recursive_walk(articles, flat_data):
        branch = []

        if not isinstance(articles, (list, tuple)):
            articles = [articles]

        for article in articles:
            if hasattr(article, "_{attribute}".format(attribute=attribute)):
                # New branch
                new_branch = new_branch_repr(
                    article,
                    recursive_walk(getattr(article, "_{attribute}"
                        .format(attribute=attribute)), flat_data))

                branch.append(new_branch)
                flat_data.append(new_branch)

            else:
                # Branch end
                end_branch = end_branch_repr(article)

                branch.append(end_branch)
                flat_data.append(end_branch)

        return branch

    tree_data = recursive_walk(articles, flat_data)
    data = tree_data if structure == "nested" else flat_data

    with open(output_filename, 'w') as fp:
        json.dump(data, fp, **kwargs)

    return True


# These functions below are just temporary and are immediately deprecated
def export_to_d3rt(paper, attribute="citations", map_func=None):
    """Export the paper provided to a JSON-format for D3.js Reingold-Tilford Tree visualisations."""

    if map_func is None:
        map_func = lambda x: x
    

    def map_as_children(articles):
        branch = []

        if not isinstance(articles, (list, tuple)):
            articles = [articles]

        for article in articles:
            if hasattr(article, "_{attribute}".format(attribute=attribute)):
                branch.append({
                    "name": map_func(article),
                    "children": map_as_children(getattr(article, "_{attribute}".format(attribute=attribute)))
                    })
            else:
                branch.append({
                    "name": map_func(article)
                    })

        return branch

    return map_as_children(paper)



def export_to_d3_heb(paper, attribute="citations", map_func=None):

    if map_func is None:
        map_func = lambda x: x

    data = []

    def map_flat(articles, data):

        if not isinstance(articles, (list, tuple)):
            articles = [articles]

        for article in articles:
            if hasattr(article, "_{attribute}".format(attribute=attribute)):
                data.append({
                    "name": map_func(article),
                    "imports": map(map_func, getattr(article, "_{attribute}".format(attribute=attribute))),
                    "size": article.citation_count
                    })

                map_flat(getattr(article, "_{attribute}".format(attribute=attribute)), data)

            else:
                # Check to see it's not a double up.
                if map_func(article) in [item["name"] for item in data]:
                    continue

                # Find out who cited this
                data.append({
                    "name": map_func(article),
                    "size": article.citation_count,
                    "imports": []
                    })

    map_flat(paper, data)
    
    # Sort the data
    data = sorted(data, key=lambda x: x["name"])

    # Do the backlinks lazily
    for item in data:
        
        if len(item["imports"]) == 0:
            imports = []
            for sub_item in data:
                if item["name"] in sub_item["imports"]:
                    imports.append(item["name"])

            item["imports"] = imports


    return data


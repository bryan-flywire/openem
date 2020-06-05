# Frequently Asked Questions

From time to time, various questions on how to use OpenEM are asked by the
community of users. This document attempts to consolidate the most asked
questions to assist new users of the library.

## Training & Data curation

OpenEM allows for flexibly deploying parts of the pipeline relevant for a
given problem set. With this complexity comes complication in understanding
what is required for a given training run. The following flowchart shows the
decision tree required for setting up training data.

![Training data flowchart](https://user-images.githubusercontent.com/47112112/68147729-b8fe3700-ff08-11e9-9637-c5269202eeed.jpg)

## Docker-related

### What is Docker?

Docker is a container management system. It allows us to package OpenEM as
a unit effectively equivilant to a light weight Virtual Machine. All system
dependencies are taken care of such that OpenEM can work with minimal
administriva.

Key terms to understand in our usage of Docker.

- Image : A Docker _image_ is the entity downloaded with a `docker pull`
  command. It is the filesystem contents of a given container.
      + To see images you have on your system, use `docker images`
- Container: A Docker _container_ is the running instance of the "Light weight VM".
      + To see running containers you have on your system, use `docker ps`


### How do I get files to/from a docker container?

It is preferred to get a file from a docker container while it is still running.
The commands provided in the `tutorial.md` file use bind mounts to expose a
directory on the host to running container.

In the following example, the folder `/mnt/md0` on the host is mounted as
`/data` to the perspective of the docker container.

`docker run --rm -ti -v /mnt/md0:/data ubuntu bash`

### I got an error like "Gtk-WARNING **: 11:14:47.519: cannot open display: ".

Because the docker container is running as an isolated environment it doesn't
have access to the windowing environment of the host (X11). For trusted images
the easiest way to facilitate this is to use the same syntax as some of the
commands in `tutorial.md` to allow the container instance to use the host
X11 network.

Specifically that entails adding `-v"$HOME/.Xauthority:/root/.Xauthority:rw" --env=DISPLAY --net=host` to the docker invocation.

The following command creates a vanilla ubuntu X11-enabled container:
`docker run --rm -ti -v"$HOME/.Xauthority:/root/.Xauthority:rw" --env=DISPLAY --net=host ubuntu bash`

*Important*: When using `--net host` the container isn't as isolated from the hosts network interface.

*Important*: The prompt of the container using the `--net host` will look
similar the host prompt. Care should be taken to avoid mistakes.

### I wanted to launch tensorboard, but I can't access the shell in the running
### container any longer.

If the container was launched with `--name openem`, then the following command
launches another bash process in the running container:

`docker exec --env=DISPLAY -it openem bash`

Substitute `openem` for what ever you named your container. If you didn't name
your container, then you need to find your running container via `docker ps`
and use:

`docker exec --env=DISPLAY -it <hash_of_container> bash`

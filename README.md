# Tensor-Cortex

Inspired by [this article](https://medium.com/@skeletrox/5-45-am-with-docker-ca029e62c272).

## Setting up

If you can get the setup in the above article running, you are good to go.

## When do I use an nvidia runtime?

If you have a ton of GPU resources and can tweak your dockers to grow as and when they need to, the nvidia GPU runtime is perfect for you. Even if you don't, it's okay to use this as long as there's only one performer.

## What does this do?

This project simply generates a set of names using a distributed LSTM system. You could technically tweak the orchestrator to act like one half of a GAN and the performers to collectively be the other half of said GAN.

## I want to improve this

Please do. Make a PR.
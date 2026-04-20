# ADR-0001 - Monolito modular con frontend separado

## Estado

Aprobado

## Contexto

El producto necesita:

- administracion de usuarios
- retrieval documental
- generacion de codigo PAC
- trazabilidad
- despliegue simple en contenedores

## Decision

Se adopta una arquitectura de monolito modular con:

- frontend separado
- backend central
- worker asincrono

## Justificacion

Esta decision reduce complejidad operativa frente a microservicios y mantiene claras las fronteras de responsabilidad.

## Consecuencias

- mas simple de desplegar al inicio
- mas facil de documentar y mantener
- suficiente para el volumen inicial del producto

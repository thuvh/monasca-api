#!/bin/bash
set -x
echo $*
# Download maven 3 if the system maven isn't maven 3
VERSION=`mvn -v | grep "Apache Maven 3"`
if [ -z "${VERSION}" ]; then
   curl http://archive.apache.org/dist/maven/binaries/apache-maven-3.2.1-bin.tar.gz > apache-maven-3.2.1-bin.tar.gz
   tar -xvzf apache-maven-3.2.1-bin.tar.gz
   MVN=${PWD}/apache-maven-3.2.1/bin/mvn
else
   MVN=mvn
fi

# Get the expected common version
COMMON_VERSION=$1
# Get rid of the version argument
shift
echo $*
echo $1

# Get rid of the java property name containing the args
shift

# Build common first but we have to do a install not package
if [ "$1" == "package" ]; then
    ( cd common; ./build_common.sh ${MVN} ${COMMON_VERSION} )
    RC=$?
    if [ $RC != 0 ]; then
        exit $RC
    fi
fi

# Invoke the maven 3 on the real pom.xml
( cd java; ${MVN} $* )
RC=$?

# Copy the jars where the publisher will find them
mkdir -p target
cp java/*/target/*.jar target

rm -fr apache-maven-3.2.1*
exit $RC

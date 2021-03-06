# Running statistics

# Author:: Sam Steingold (<sds@magnetic.com>)
# Copyright:: Copyright (c) 2014, 2015, 2016 Magnetic Media Online, Inc.
# License:: Apache License, Version 2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import util
import sys

class RunStat (object):
    def __init__ (self, title):
        self.title = title

    def add (self, observation, n):
        raise NotImplementedError("RunStat.add")

    def num (self):             # total number of observations added
        raise NotImplementedError("RunStat.num")

    def merge (self, rs):
        if self.title != rs.title:
            raise ValueError("RunStat.merge: title mismatch",self.title,rs.title)

    def out (self):
        raise NotImplementedError("RunStat.out")

class Counter (RunStat):
    def __init__ (self, title, values = None, values_weights = None):
        super(Counter, self).__init__(title)
        self.counts = dict()
        if values is not None:
            for v in values:
                self.add(v)
        if values_weights is not None:
            for v,w in values_weights:
                self.add(v,w)

    def add (self, observation, n = 1):
        if isinstance(self.title,tuple) and (
                not isinstance(observation,tuple) or len(self.title) != len(observation)):
            raise ValueError("Counter.add: incompatible observation",self.title,observation)
        self.counts[observation] = self.counts.get(observation,0) + n

    def num (self):
        return sum(self.counts.itervalues())

    def entropy (self, scaledto1 = False):
        return util.dict_entropy(self.counts, scaledto1=scaledto1)

    def merge (self, c):
        super(Counter, self).merge(c)
        if not isinstance(c, Counter):
            raise ValueError("Counter.merge: bad type",type(c))
        for o,n in c.counts.iteritems():
            self.add(o, n)

    def split (self):
        "Split a counter of pairs into a pair of counters"
        (t1, t2) = self.title
        r1 = Counter(t1)
        r2 = Counter(t2)
        for (o1,o2),n in self.counts.iteritems():
            r1.add(o1, n)
            r2.add(o2, n)
        return (r1,r2)

    def __str__ (self):
        return "%s (%s)" % (self.title,util.dict__str__(
            self.counts,util.title2missing(self.title)))

    def __repr__ (self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    # pylint: disable=arguments-differ
    def out (self, pc = util.PrintCounter()):
        if pc is None:
            pc = util.PrintCounter()
        return pc.out(self.counts, self.title)

    def csv (self, csv, logger=None, smallest=0):
        util.PrintCounter.csv(self.counts, self.title, csv, logger=logger, smallest=smallest)

    def dump (self, pc, csv, logger=None, csvsmallest=0):
        if pc.out(self.counts,self.title) and csv is not None:
            self.csv(csv, logger=logger, smallest=csvsmallest)

    def short (self):
        return "{t:s}:{n:,d}/{c:,d}".format(
            t=self.title,n=self.num(),c=len(self.counts))

    @staticmethod
    def test ():
        c = Counter("foo")
        for x in ['a','b','a','c','a','b']:
            c.add(x)
        pc = util.PrintCounter()
        c.out(pc)
        d = Counter("foo", values=['c','d','e','c',None,'a','b',None])
        d.out(pc)
        d.csv(sys.stdout)
        c.merge(d)
        c.out(pc)
        e = Counter("bar")
        try:
            e.merge(c)
        except Exception as ex:
            print ex
        try:
            e.merge(c)
        except Exception as ex:
            print ex
        c.add("123")
        c.add("a",3)
        c.add("b",1)
        c.out()
        try:
            c.merge(e)
        except Exception as ex:
            print ex
        c = Counter(('a','b'))
        c.add(('a1','b1'))
        try:
            c.add(('a1','b1','d'))
        except Exception as ex:
            print ex
        c.add(('a1','b1'))
        c.add(('a1','b2'))
        c.out()
        c.csv(sys.stdout)
        p1,p2 = c.split()
        p1.out(pc)
        p2.out(pc)


class NumStat (RunStat):
    def __init__ (self, title, values = None, values_weights = None, integer = False):
        super(NumStat, self).__init__(title)
        self.count = 0
        self.minV = float("inf")
        self.minN = 0
        self.maxV = float("-inf")
        self.maxN = 0
        self.sumV = 0
        self.sum2 = 0
        self.nanCount = 0
        self.integer = integer  # if true, min/max is printed with {0:,d}
        self.bad = None
        if values is not None:
            for v in values:
                self.add(v)
        if values_weights is not None:
            for v,w in values_weights:
                self.add(v,w)

    def add (self, v, n = 1):
        try:
            v = float(v)
        except (TypeError, ValueError):
            if self.bad is None:
                self.bad = Counter("{}(bad)".format(self.title))
            self.bad.add(v,n)
            return
        if math.isnan(v):
            self.nanCount += n
        else:
            self.count += n
            self.sumV += v * n
            self.sum2 += v*v * n
            if self.minV == v:
                self.minN += n
            elif self.minV > v:
                self.minV = v
                self.minN = n
            if self.maxV == v:
                self.maxN += n
            elif self.maxV < v:
                self.maxV = v
                self.maxN = n

    def num (self):
        return self.nanCount + self.count + (0 if self.bad is None else self.bad.num())

    def merge (self, ns):
        super(NumStat, self).merge(ns)
        if isinstance(ns, NumStat):
            self.count += ns.count
            if self.minV == ns.minV:
                self.minN += ns.minN
            elif self.minV > ns.minV:
                self.minV = ns.minV
                self.minN = ns.minN
            if self.maxV == ns.maxV:
                self.maxN += ns.maxN
            elif self.maxV < ns.maxV:
                self.maxV = ns.maxV
                self.maxN = ns.maxN
            self.sumV += ns.sumV
            self.sum2 += ns.sum2
            self.nanCount += ns.nanCount
        elif isinstance(ns, Counter):
            for x,n in ns.counts.iteritems():
                self.add(x,n)

    def mean (self):
        if self.count == 0:
            return float("NaN")
        return self.sumV / self.count

    def stdDev (self):
        if self.count == 0:
            return float("NaN")
        if (self.maxV - self.minV) < sys.float_info.epsilon * self.sum2:
            return 0 # guard against roundoff errors producing sqrt(-eps)
        return math.sqrt(self.sum2 / self.count -
                         (self.sumV * self.sumV) / (self.count * self.count))


    def __str__ (self, toString = str):
        if toString is None:
            toString = str
        return "{t:s} [{c:,.0f} {m:s}${d:s} {i:s}{I:s}:{a:s}{A:s}{n:s}{b:s}]".format(
            t=self.title,c=self.count,m=toString(self.mean()),
            d=toString(self.stdDev()),
            i=("{i:,.0f}".format(i=self.minV) if self.integer else
               toString(self.minV)),
            I=("" if self.minN == 1 else "*{i:,.0f}".format(i=self.minN)),
            a=("{i:,.0f}".format(i=self.maxV) if self.integer else
               toString(self.maxV)),
            A=("" if self.maxN == 1 else "*{i:,.0f}".format(i=self.maxN)),
            n=("" if self.nanCount==0 else " NaN={i:,.0f}".format(i=self.nanCount)),
            b=("" if self.bad is None else " Bad={i:,.0f}".format(i=self.bad.num())))

    def __repr__ (self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    # pylint: disable=arguments-differ
    def out (self, pc = util.PrintCounter(), toString = str):
        print pc.header+" "+self.__str__(toString)
        if self.bad is None:
            return False # full output, no truncation
        return self.bad.out(pc)

    def dump (self, pc, toString = str):
        self.out(pc,toString)

    def as_dict (self):
        if self.bad:
            ret = self.__dict__.copy()
            ret["bad"] = self.bad.counts
            return ret
        return self.__dict__

    @staticmethod
    def test ():
        c = NumStat("foo")
        for x in [1,2,1,3,0,0,0,0,float("NaN")]:
            c.add(x)
        c.out()
        print "c.num={n:,d}".format(n=c.num())
        d = NumStat("foo",values=[5,6,8,3,4,5,2,4,5,6,7,4,4,5])
        d.out()
        print c.as_dict()
        c.merge(d)
        c.out()
        print c.as_dict()
        for x in [100,200,10000,300000]:
            c.add(x)
        import progress
        c.out(toString=progress.difftime2string)
        print "c.num={n:,d}".format(n=c.num())
        print c.as_dict()

def test():
    Counter.test()
    NumStat.test()
    c = Counter("foo")
    c.add(1)
    c.add("2")
    c.add("a")
    n = NumStat("foo")
    n.add(1)
    try:
        c.merge(n)
    except Exception as ex:
        print ex
    n.merge(c)
    n.out()

if __name__ == '__main__':
    test()

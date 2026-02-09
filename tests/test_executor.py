import unittest
import os
import sys
import logging

# Adjusting path to point to the new src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import Place, Transition, Arc, ArcType
from pypneu.executor import PetriNetExecution, StochasticPetriNetExecution

logging.basicConfig(level=logging.DEBUG)


class TestComplexPetriNetExecution(unittest.TestCase):

    def test_conflict_resolution_by_story(self):
        """Conflict: P1 can feed T1 OR T2. Story should decide."""
        p1 = Place("p1", True)
        p_out1 = Place("out1")
        p_out2 = Place("out2")
        t1 = Transition("t1")
        t2 = Transition("t2")

        Arc(p1, t1, ArcType.ENABLER)
        Arc(t1, p_out1, ArcType.ENABLER)
        Arc(p1, t2, ArcType.ENABLER)
        Arc(t2, p_out2, ArcType.ENABLER)

        # Story forces t2 to win the conflict
        net = PetriNetExecution(places=[p1, p_out1, p_out2], transitions=[t1, t2], story=["t2"])
        net.run_simulation(10)

        self.assertTrue(p_out2.marking)
        self.assertFalse(p_out1.marking)

    def test_bus_partial_inhibition(self):
        """Bus Sync: If one transition in a bus is inhibited, the whole bus fails to fire."""
        p_in1 = Place("in1", True)
        p_in2 = Place("in2", True)
        p_block = Place("block", True)  # Inhibitor active

        t1 = Transition("bus")
        t2 = Transition("bus")

        Arc(p_in1, t1, ArcType.ENABLER)
        Arc(p_in2, t2, ArcType.ENABLER)
        Arc(p_block, t1, ArcType.INHIBITOR)  # Blocks ONLY t1

        net = PetriNetExecution(places=[p_in1, p_in2, p_block], transitions=[t1, t2])

        # Whole bus should fail
        steps = net.run_simulation(5)
        self.assertEqual(steps, 0)
        self.assertTrue(p_in1.marking)
        self.assertTrue(p_in2.marking)

    def test_self_loop_reset(self):
        """Self-loop: T1 consumes P1 and produces P1. Mark stays True."""
        p1 = Place("p1", True)
        t1 = Transition("t1")
        Arc(p1, t1, ArcType.ENABLER)
        Arc(t1, p1, ArcType.ENABLER)

        net = PetriNetExecution(places=[p1], transitions=[t1])
        net.run_simulation(1)
        self.assertTrue(p1.marking, "P1 should be restored by output arc")

    def test_multi_place_requirement(self):
        """Logical AND: T1 requires P1 AND P2 to fire."""
        p1 = Place("p1", True)
        p2 = Place("p2", False)  # Missing
        t1 = Transition("t1")
        Arc(p1, t1, ArcType.ENABLER)
        Arc(p2, t1, ArcType.ENABLER)

        net = PetriNetExecution(places=[p1, p2], transitions=[t1])
        self.assertEqual(net.run_simulation(5), 0, "Should not fire without both tokens")

    def test_inhibitor_cascade(self):
        """P1 -> T1 -> P2. P2 inhibits T2. T2 should only fire after T1 clears it (or before T1)."""
        p1 = Place("p1", True)
        p2 = Place("p2", False)
        t1 = Transition("t1")
        t2 = Transition("source_t2")  # Source

        Arc(p1, t1, ArcType.ENABLER)
        Arc(t1, p2, ArcType.ENABLER)
        Arc(p2, t2, ArcType.INHIBITOR)

        net = PetriNetExecution(places=[p1, p2], transitions=[t1, t2], story=["source_t2", "t1", "source_t2"])

        # 1. source_t2 fires (p2 is empty)
        # 2. t1 fires (p2 becomes full)
        # 3. source_t2 fails (p2 is full)
        steps = net.run_simulation(10)
        self.assertEqual(steps, 2)

    def test_deadlock_scenario(self):
        """Classic deadlock: T1 needs P2, T2 needs P1. Both empty."""
        p1 = Place("p1")
        p2 = Place("p2")
        t1 = Transition("t1");
        Arc(p2, t1, ArcType.ENABLER)
        t2 = Transition("t2");
        Arc(p1, t2, ArcType.ENABLER)

        net = PetriNetExecution(places=[p1, p2], transitions=[t1, t2])
        self.assertEqual(net.run_simulation(10), 0)

    def test_alternating_bit_protocol_sync(self):
        """Tests a producer-consumer sync where the 'channel' must be empty (inhibitor) to send."""
        p_ready = Place("ready", True)
        p_channel = Place("channel", False)
        p_received = Place("received")

        t_send = Transition("send")
        Arc(p_ready, t_send, ArcType.ENABLER)
        Arc(p_channel, t_send, ArcType.INHIBITOR)  # Send only if channel empty
        Arc(t_send, p_channel, ArcType.ENABLER)

        t_receive = Transition("receive")
        Arc(p_channel, t_receive, ArcType.ENABLER)
        Arc(t_receive, p_received, ArcType.ENABLER)

        net = PetriNetExecution(places=[p_ready, p_channel, p_received], transitions=[t_send, t_receive])

        # Step 1: Send. Step 2: Receive.
        self.assertEqual(net.run_simulation(5), 2)
        self.assertTrue(p_received.marking)

    def test_bus_fan_out(self):
        """Bus Sync: One input place triggers a bus that populates three different output places."""
        p_in = Place("in", True)
        out_places = [Place(f"out{i}") for i in range(3)]
        transitions = [Transition("fan_bus") for _ in range(3)]

        for i in range(3):
            Arc(p_in, transitions[i], ArcType.ENABLER)
            Arc(transitions[i], out_places[i], ArcType.ENABLER)

        net = PetriNetExecution(places=[p_in] + out_places, transitions=transitions)
        net.run_simulation(1)

        # All outputs should be marked because the bus fired as a single unit
        for p in out_places:
            self.assertTrue(p.marking)

    def test_catalyst_chain(self):
        """Place C is a catalyst for T1, and T1 produces a token for T2."""
        c = Place("cat", True)
        p1 = Place("p1", True)
        p2 = Place("p2")
        t1 = Transition("t1")
        t2 = Transition("t2")

        # T1 catalyst
        Arc(c, t1, ArcType.ENABLER);
        Arc(t1, c, ArcType.ENABLER)
        Arc(p1, t1, ArcType.ENABLER)
        # T1 -> T2
        p_mid = Place("mid")
        Arc(t1, p_mid, ArcType.ENABLER)
        Arc(p_mid, t2, ArcType.ENABLER)
        Arc(t2, p2, ArcType.ENABLER)

        net = PetriNetExecution(places=[c, p1, p_mid, p2], transitions=[t1, t2])
        self.assertEqual(net.run_simulation(10), 2)
        self.assertTrue(p2.marking)
        self.assertTrue(c.marking)

    def test_story_override_natural_firing(self):
        """Test that if a story specifies a transition that isn't enabled, simulation stops."""
        p1 = Place("p1", False)  # NOT enabled
        t1 = Transition("t1")
        Arc(p1, t1, ArcType.ENABLER)

        net = PetriNetExecution(places=[p1], transitions=[t1], story=["t1"])

        # Even if iterations=10, it should fire 0 times because t1 is requested but blocked
        self.assertEqual(net.run_simulation(10), 0)

    def test_stochastic_distribution(self):
        """Conflict: P1 -> T1 or T2. Over 100 runs, both should fire."""
        t1_count = 0
        t2_count = 0

        for _ in range(100):
            # Initial marking: 1 token in p1
            p1 = Place("p1", 1)
            out1 = Place("out1")
            out2 = Place("out2")

            t1 = Transition("t1")
            # USE STANDARD CONSUMING ARCS
            Arc(p1, t1)
            Arc(t1, out1)

            t2 = Transition("t2")
            # USE STANDARD CONSUMING ARCS
            Arc(p1, t2)
            Arc(t2, out2)

            executor = StochasticPetriNetExecution(
                places=[p1, out1, out2],
                transitions=[t1, t2]
            )
            executor.run_simulation(iterations=1)

            if out1.marking: t1_count += 1
            if out2.marking: t2_count += 1

        print(f"Distribution - T1: {t1_count}, T2: {t2_count}")
        self.assertGreater(t1_count, 0)
        self.assertGreater(t2_count, 0)

if __name__ == '__main__':
    unittest.main()
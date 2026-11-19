import unittest

from app.experiment.winner import decide_winner


class DecisionMakerTests(unittest.TestCase):
    def test_clear_vote2_winner(self):
        # Vote 1 points elsewhere; only vote 2 counts when it has a single leader.
        vote1 = {1: 3, 2: 0, 3: 0}
        vote2 = {1: 0, 2: 2, 3: 1}
        winner, how = decide_winner(vote1, vote2, choose=self._must_not_be_called)
        self.assertEqual((winner, how), (2, "vote2"))

    def test_vote2_tie_resolved_by_vote1(self):
        # Slots 1 and 3 tie on vote 2; slot 3 led vote 1, so it wins. Slot 2 led
        # vote 1 overall but was not in the vote 2 tie, so it must not be considered.
        vote1 = {1: 0, 2: 2, 3: 1}
        vote2 = {1: 1, 2: 0, 3: 1}
        winner, how = decide_winner(vote1, vote2, choose=self._must_not_be_called)
        self.assertEqual((winner, how), (3, "vote1"))

    def test_tie_after_vote1_uses_controlled_random_pick_among_tied(self):
        # Slots 1 and 2 tie on both votes; slot 3 is out of it. The random pick must
        # be offered exactly the tied candidates, and its choice is the winner.
        vote1 = {1: 1, 2: 1, 3: 0}
        vote2 = {1: 2, 2: 2, 3: 0}
        offered = []

        def controlled_pick(candidates):
            offered.append(list(candidates))
            return candidates[-1]

        winner, how = decide_winner(vote1, vote2, choose=controlled_pick)
        self.assertEqual(offered, [[1, 2]])
        self.assertEqual((winner, how), (2, "random"))

    @staticmethod
    def _must_not_be_called(candidates):
        raise AssertionError(f"random pick should not be needed, got {candidates}")


if __name__ == "__main__":
    unittest.main()

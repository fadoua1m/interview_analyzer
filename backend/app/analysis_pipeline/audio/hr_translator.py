"""
Translates raw audio metrics into HR-friendly insights.
Bridges the gap between technical audio analysis and recruiter understanding.
"""
from typing import Dict


class HRMetricsTranslator:
    """Converts raw audio features into HR recruiter language."""
    
    @staticmethod
    def confidence_level(
        filler_percentage: float,
        hesitation_count: int,
        pitch_range: float,
        speech_rate_consistency: float,
    ) -> Dict:
        """
        Compute confidence level from multiple signals.
        
        Args:
            filler_percentage: % of speech that is fillers (0-50)
            hesitation_count: Number of pauses >1 second
            pitch_range: Pitch variation in Hz (higher = more variation)
            speech_rate_consistency: 0-100 (100 = perfect consistency)
        
        Returns:
            {
                "level": "High|Medium|Low",
                "score": 0-100,
                "factors": [reason1, reason2, ...]
            }
        """
        factors = []
        scores = []
        
        # Filler word analysis
        filler_score = max(0, 100 - (filler_percentage * 3.5))  # cap at 100
        scores.append(filler_score * 0.3)
        if filler_percentage < 3:
            factors.append("Minimal filler words (confident speech)")
        elif filler_percentage < 7:
            factors.append("Occasional filler words (moderate confidence)")
        else:
            factors.append(f"High filler word usage ({filler_percentage}%) - nervousness")
        
        # Hesitation analysis
        hesitation_score = max(0, 100 - (hesitation_count * 8))  # each long pause = -8
        scores.append(hesitation_score * 0.25)
        if hesitation_count < 2:
            factors.append("Minimal hesitations (composed)")
        elif hesitation_count < 5:
            factors.append(f"{hesitation_count} hesitations (slightly nervous)")
        else:
            factors.append(f"{hesitation_count} long pauses (significant uncertainty)")
        
        # Pitch variation (wider range = more engaged/confident)
        pitch_score = min(100, (pitch_range / 80) * 100) if pitch_range > 0 else 50
        scores.append(pitch_score * 0.25)
        if pitch_range > 60:
            factors.append("Wide pitch variation (engaged and confident)")
        elif pitch_range > 30:
            factors.append("Moderate pitch variation (engaged)")
        else:
            factors.append("Narrow pitch variation (flat/disengaged tone)")
        
        # Speech rate consistency
        scores.append(speech_rate_consistency * 0.2)
        if speech_rate_consistency > 85:
            factors.append("Consistent speech rate (controlled delivery)")
        elif speech_rate_consistency > 70:
            factors.append("Fairly consistent speech rate")
        else:
            factors.append("Inconsistent speech rate (potential nervousness)")
        
        avg_score = sum(scores) if scores else 50
        
        if avg_score >= 75:
            level = "High"
        elif avg_score >= 55:
            level = "Medium"
        else:
            level = "Low"
        
        return {
            "level": level,
            "score": round(avg_score, 1),
            "factors": factors,
        }
    
    @staticmethod
    def communication_clarity(
        speech_rate: float,
        pause_ratio: float,
        energy_variation: float,
        articulation_clarity: float = 80.0,
        language: str = "en",
    ) -> Dict:
        """
        Compute communication clarity level.
        
        Args:
            speech_rate: Words per minute
            pause_ratio: Proportion of time spent pausing (0-1)
            energy_variation: Standard deviation of RMS energy
            articulation_clarity: 0-100 (from acoustic analysis)
        
        Returns:
            {
                "level": "Clear|Acceptable|Unclear",
                "score": 0-100,
                "factors": [...]
            }
        """
        factors = []
        scores = []
        
        # Speech rate analysis (language-aware WPM ranges)
        if language == "fr":
            ideal_min, ideal_max = 110, 145
            good_min, good_max = 95, 165
        else:
            ideal_min, ideal_max = 120, 150
            good_min, good_max = 100, 170

        if ideal_min <= speech_rate <= ideal_max:
            rate_score = 95
            factors.append(f"Optimal speech rate ({speech_rate:.0f} wpm)")
        elif good_min <= speech_rate <= good_max:
            rate_score = 85
            factors.append(f"Good speech rate ({speech_rate:.0f} wpm)")
        elif speech_rate < good_min:
            rate_score = 70
            factors.append(f"Slow speech rate ({speech_rate:.0f} wpm) - may seem unclear")
        else:
            rate_score = 70
            factors.append(f"Fast speech rate ({speech_rate:.0f} wpm) - may seem rushed")
        scores.append(rate_score * 0.3)
        
        # Pause pattern (ideal: 15-25% natural pausing)
        if 0.15 <= pause_ratio <= 0.25:
            pause_score = 90
            factors.append("Natural pause pattern (well-paced)")
        elif 0.10 <= pause_ratio <= 0.30:
            pause_score = 75
            factors.append("Acceptable pause pattern")
        elif pause_ratio < 0.10:
            pause_score = 65
            factors.append("Minimal pauses (rushed delivery)")
        else:
            pause_score = 60
            factors.append("Excessive pausing (unclear delivery)")
        scores.append(pause_score * 0.25)
        
        # Energy consistency (should be high variation = dynamic)
        if energy_variation > 0.015:
            energy_score = 85
            factors.append("Dynamic energy - engaging delivery")
        elif energy_variation > 0.008:
            energy_score = 70
            factors.append("Moderate energy variation")
        else:
            energy_score = 55
            factors.append("Low energy variation (flat, monotone delivery)")
        scores.append(energy_score * 0.2)
        
        # Articulation score
        scores.append(articulation_clarity * 0.25)
        if articulation_clarity > 85:
            factors.append("Excellent articulation and diction")
        elif articulation_clarity > 70:
            factors.append("Good articulation")
        else:
            factors.append("Articulation issues - may be unclear")
        
        avg_score = sum(scores) if scores else 50
        
        if avg_score >= 80:
            level = "Clear"
        elif avg_score >= 60:
            level = "Acceptable"
        else:
            level = "Unclear"
        
        return {
            "level": level,
            "score": round(avg_score, 1),
            "factors": factors,
        }
    
    @staticmethod
    def response_quality(
        word_count: int,
        expected_word_count: int,
        sentence_completion_rate: float,
        speech_duration: float,
        total_duration: float,
    ) -> Dict:
        """
        Assess answer quality and preparedness.
        
        Args:
            word_count: Actual words spoken
            expected_word_count: Baseline (e.g., 150 for full answer)
            sentence_completion_rate: % of sentences completed (0-100)
            speech_duration: Seconds of actual speech
            total_duration: Total time allocated
        
        Returns:
            {
                "quality_level": 0-100,
                "completeness": "Complete|Partial|Brief",
                "factors": [...]
            }
        """
        factors = []
        scores = []
        
        # Word count completeness
        completeness_ratio = min(1.0, word_count / max(expected_word_count, 1))
        if completeness_ratio >= 0.80:
            word_score = 90
            factors.append(f"Comprehensive answer ({word_count} words)")
        elif completeness_ratio >= 0.50:
            word_score = 70
            factors.append(f"Adequate answer ({word_count} words)")
        elif completeness_ratio >= 0.30:
            word_score = 50
            factors.append(f"Brief answer ({word_count} words) - lacks detail")
        else:
            word_score = 30
            factors.append(f"Very brief ({word_count} words) - superficial")
        scores.append(word_score * 0.35)
        
        # Sentence completion
        if sentence_completion_rate >= 90:
            sentence_score = 90
            factors.append("Well-organized thoughts, complete sentences")
        elif sentence_completion_rate >= 70:
            sentence_score = 75
            factors.append("Mostly complete sentences")
        elif sentence_completion_rate >= 50:
            sentence_score = 55
            factors.append(f"Trailing off/incomplete sentences ({sentence_completion_rate:.0f}% completion)")
        else:
            sentence_score = 30
            factors.append("Frequently incomplete or scattered thoughts")
        scores.append(sentence_score * 0.3)
        
        # Speech efficiency
        time_utilization = (speech_duration / max(total_duration, 1)) * 100
        if 75 <= time_utilization <= 95:
            time_score = 85
            factors.append(f"Efficient use of time ({time_utilization:.0f}%)")
        elif 50 <= time_utilization <= 75:
            time_score = 70
            factors.append(f"Comfortable pacing ({time_utilization:.0f}% speech)")
        elif time_utilization < 50:
            time_score = 50
            factors.append(f"Under-utilized time ({time_utilization:.0f}% speech) - hesitant")
        else:
            time_score = 60
            factors.append("Used most of available time")
        scores.append(time_score * 0.35)
        
        avg_score = sum(scores) if scores else 50
        
        if completeness_ratio >= 0.75:
            completeness = "Complete"
        elif completeness_ratio >= 0.50:
            completeness = "Partial"
        else:
            completeness = "Brief"
        
        return {
            "quality_level": round(avg_score, 1),
            "completeness": completeness,
            "factors": factors,
        }
    
    @staticmethod
    def stress_indicators(
        pitch_std: float,
        long_pause_count: int,
        speech_rate_consistency: float,
        energy_level: float,
    ) -> Dict:
        """
        Detect stress and anxiety signals.
        
        Args:
            pitch_std: Standard deviation of pitch (Hz)
            long_pause_count: Pauses >2 seconds
            speech_rate_consistency: 0-100 consistency score from measured intervals
            energy_level: Average RMS energy
        
        Returns:
            {
                "level": "Calm|Moderate|High",
                "score": 0-100 (100 = very calm, 0 = very stressed),
                "factors": [...]
            }
        """
        factors = []
        scores = []
        
        # Pitch stability
        if pitch_std < 30:
            pitch_score = 85
            factors.append("Stable pitch (calm demeanor)")
        elif pitch_std < 60:
            pitch_score = 65
            factors.append("Moderate pitch variation (some tension)")
        else:
            pitch_score = 40
            factors.append(f"High pitch variation ({pitch_std:.0f} Hz) - stress indicator")
        scores.append(pitch_score * 0.25)
        
        # Long pauses (silence >2 sec may indicate stress)
        if long_pause_count == 0:
            pause_score = 90
            factors.append("No extended silences")
        elif long_pause_count <= 2:
            pause_score = 75
            factors.append(f"{long_pause_count} brief moments of silence")
        elif long_pause_count <= 5:
            pause_score = 50
            factors.append(f"{long_pause_count} extended pauses - possible stress")
        else:
            pause_score = 25
            factors.append(f"{long_pause_count} long pauses - significant struggle")
        scores.append(pause_score * 0.3)
        
        # Measured speech rate consistency (no synthetic early/late estimates)
        consistency = max(0.0, min(100.0, float(speech_rate_consistency)))
        if consistency >= 85:
            consistency_score = 85
            factors.append("Consistent speech rate throughout")
        elif consistency >= 70:
            consistency_score = 70
            factors.append("Moderately consistent speech rate")
        else:
            consistency_score = 50
            factors.append("Inconsistent speech rate pattern")
        scores.append(consistency_score * 0.25)
        
        # Energy level
        if energy_level > 0.02:
            energy_score = 80
            factors.append("Strong vocal energy (confident)")
        elif energy_level > 0.01:
            energy_score = 65
            factors.append("Moderate vocal energy")
        else:
            energy_score = 40
            factors.append("Low vocal energy (withdrawn/stressed)")
        scores.append(energy_score * 0.2)
        
        avg_score = sum(scores) if scores else 50
        
        if avg_score >= 75:
            level = "Calm"
        elif avg_score >= 55:
            level = "Moderate"
        else:
            level = "High"
        
        return {
            "level": level,
            "score": round(avg_score, 1),
            "factors": factors,
        }
    
    @staticmethod
    def professionalism_signals(
        audio_clarity_score: float,  # 0-100 (STOI)
        signal_to_noise_ratio: float,  # dB
    ) -> Dict:
        """
        Assess professionalism from audio quality.
        
        Args:
            audio_clarity_score: Intelligibility (0-100, from STOI/PESQ)
            signal_to_noise_ratio: dB (higher = cleaner)
        
        Returns:
            {
                "audio_clarity": "Clean|Acceptable|Poor",
                "environment_quality": "Professional|Casual|Noisy",
                "intelligibility_score": 0-100,
                "factors": [...]
            }
        """
        factors = []
        
        # Audio clarity
        if audio_clarity_score >= 90:
            clarity_level = "Clean"
            factors.append("Excellent audio clarity (uses quality equipment)")
        elif audio_clarity_score >= 75:
            clarity_level = "Acceptable"
            factors.append("Good audio clarity")
        else:
            clarity_level = "Poor"
            factors.append(f"Audio clarity issues ({audio_clarity_score:.0f}%) - difficult to assess")
        
        # Signal-to-noise ratio
        if signal_to_noise_ratio > 20:
            env_level = "Professional"
            factors.append("Clean environment (minimal background noise)")
        elif signal_to_noise_ratio > 10:
            env_level = "Casual"
            factors.append("Some background noise (casual setup)")
        else:
            env_level = "Noisy"
            factors.append(f"Significant noise ({signal_to_noise_ratio:.1f} dB SNR) - distracting")
        
        return {
            "audio_clarity": clarity_level,
            "environment_quality": env_level,
            "intelligibility_score": round(audio_clarity_score, 1),
            "factors": factors,
        }

    @staticmethod
    def recommendation(
        confidence_level: str,
        communication_clarity: str,
        stress_indicators: str,
        audio_clarity: str,
    ) -> str:
        if confidence_level == "High" and communication_clarity == "Clear" and audio_clarity in {"Clean", "Acceptable"}:
            return "Excellent audio presence. Suitable for client-facing role."
        if communication_clarity == "Unclear" or audio_clarity == "Poor":
            return "Audio delivery needs improvement before client-facing responsibilities."
        if stress_indicators == "High":
            return "Promising profile with elevated stress indicators; consider a follow-up round."
        return "Audio performance is acceptable for general collaboration roles."
    
    @staticmethod
    def overall_audio_narrative(
        confidence: Dict,
        clarity: Dict,
        response_quality: Dict,
        stress: Dict,
        professionalism: Dict,
    ) -> str:
        """
        Generate a single HR-friendly narrative from all metrics.
        """
        narratives = []
        
        # Confidence narrative
        conf_level = confidence.get("level", "Unknown")
        conf_score = confidence.get("score", 0)
        if conf_level == "High":
            narratives.append(f"Candidate demonstrates high confidence ({conf_score}/100) with composed speech patterns.")
        elif conf_level == "Medium":
            narratives.append(f"Candidate shows moderate confidence ({conf_score}/100) with some nervousness signals.")
        else:
            narratives.append(f"Candidate appears nervous ({conf_score}/100) with multiple anxiety markers.")
        
        # Clarity narrative
        clarity_level = clarity.get("level", "Unknown")
        if clarity_level == "Clear":
            narratives.append("Communication is clear and well-articulated.")
        elif clarity_level == "Acceptable":
            narratives.append("Communication is reasonably clear with acceptable pacing.")
        else:
            narratives.append("Communication has clarity issues affecting understanding.")
        
        # Response quality narrative
        quality = response_quality.get("quality_level", 0)
        completeness = response_quality.get("completeness", "Unknown")
        if quality >= 80:
            narratives.append(f"Provides thoughtful, well-developed {completeness.lower()} answers with good detail.")
        elif quality >= 60:
            narratives.append(f"Provides {completeness.lower()} answers with adequate substance.")
        else:
            narratives.append(f"Responses are {completeness.lower()} and lack sufficient depth.")
        
        # Stress narrative
        stress_level = stress.get("level", "Unknown")
        if stress_level == "Calm":
            narratives.append("Remains calm and composed throughout interview.")
        elif stress_level == "Moderate":
            narratives.append("Shows some stress signals but maintains professionalism.")
        else:
            narratives.append("Displays significant stress indicators. May benefit from more preparation.")
        
        # Professionalism narrative
        prof = professionalism.get("audio_clarity", "Unknown")
        env = professionalism.get("environment_quality", "Unknown")
        if prof == "Clean" and env == "Professional":
            narratives.append("Professional setup and audio quality suggest thorough preparation.")
        elif prof == "Acceptable" and env == "Casual":
            narratives.append("Adequate audio setup, casual environment.")
        else:
            narratives.append(f"Audio quality {prof.lower()}, environment {env.lower()}.")
        
        return " ".join(narratives)
